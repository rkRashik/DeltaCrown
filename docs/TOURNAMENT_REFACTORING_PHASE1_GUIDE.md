# 🚀 Tournament Refactoring - Phase 1 Implementation Guide

**Goal:** Create structured models and migrate existing data  
**Timeline:** 2 weeks  
**Status:** Ready to implement

---

## Phase 1 Overview

Create new models to organize tournament data logically:
1. TournamentSchedule - All date/time fields
2. TournamentCapacity - Participant limits and registration settings
3. TournamentFinance - Entry fees and prizes
4. TournamentMedia - Images and visual assets
5. TournamentRules - Format and rules
6. TournamentArchive - Complete archive system ⚡

---

## Step 1: Create New Models

### A. Create model files

**1. Create directory structure:**
```bash
mkdir apps/tournaments/models/core
```

**2. Create files:**
- `apps/tournaments/models/core/__init__.py`
- `apps/tournaments/models/core/tournament_schedule.py`
- `apps/tournaments/models/core/tournament_capacity.py`
- `apps/tournaments/models/core/tournament_finance.py`
- `apps/tournaments/models/core/tournament_media.py`
- `apps/tournaments/models/core/tournament_rules.py`
- `apps/tournaments/models/core/tournament_archive.py`

### B. Implementation Order

**Priority 1: TournamentSchedule** (Most critical)
```python
# apps/tournaments/models/core/tournament_schedule.py
from django.db import models
from django.core.exceptions import ValidationError


class TournamentSchedule(models.Model):
    """
    All date/time fields for a tournament.
    Separates timing logic from core tournament model.
    """
    tournament = models.OneToOneField(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='schedule',
        primary_key=True
    )
    
    # Registration window
    registration_opens_at = models.DateTimeField(
        help_text="When registration opens"
    )
    registration_closes_at = models.DateTimeField(
        help_text="When registration closes"
    )
    
    # Check-in window (optional)
    checkin_opens_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When check-in opens (minutes before tournament start)"
    )
    checkin_closes_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When check-in closes (minutes before tournament start)"
    )
    
    # Tournament window
    tournament_starts_at = models.DateTimeField(
        help_text="When tournament begins"
    )
    tournament_ends_at = models.DateTimeField(
        help_text="Expected tournament end time"
    )
    
    # Timezone
    timezone = models.CharField(
        max_length=50,
        default='Asia/Dhaka',
        help_text="Timezone for all dates/times"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tournament_schedules'
        verbose_name = 'Tournament Schedule'
        verbose_name_plural = 'Tournament Schedules'
    
    def __str__(self):
        return f"Schedule for {self.tournament.name}"
    
    def clean(self):
        """Validate schedule logic."""
        errors = {}
        
        # Registration window validation
        if self.registration_opens_at and self.registration_closes_at:
            if self.registration_opens_at >= self.registration_closes_at:
                errors['registration_closes_at'] = 'Must be after registration opens'
        
        # Tournament window validation
        if self.tournament_starts_at and self.tournament_ends_at:
            if self.tournament_starts_at >= self.tournament_ends_at:
                errors['tournament_ends_at'] = 'Must be after tournament starts'
        
        # Registration must close before tournament starts
        if self.registration_closes_at and self.tournament_starts_at:
            if self.registration_closes_at > self.tournament_starts_at:
                errors['registration_closes_at'] = 'Must close before tournament starts'
        
        # Check-in validation
        if self.checkin_opens_at and self.checkin_closes_at:
            if self.checkin_opens_at >= self.checkin_closes_at:
                errors['checkin_closes_at'] = 'Must be after check-in opens'
        
        if errors:
            raise ValidationError(errors)
    
    @property
    def is_registration_open(self) -> bool:
        """Check if registration is currently open."""
        from django.utils import timezone
        now = timezone.now()
        return self.registration_opens_at <= now <= self.registration_closes_at
    
    @property
    def is_tournament_live(self) -> bool:
        """Check if tournament is currently running."""
        from django.utils import timezone
        now = timezone.now()
        return self.tournament_starts_at <= now <= self.tournament_ends_at
```

**Priority 2: TournamentCapacity**
```python
# apps/tournaments/models/core/tournament_capacity.py
from django.db import models
from django.core.exceptions import ValidationError


class TournamentCapacity(models.Model):
    """
    Participant limits and registration settings.
    Defines how many can register and in what format.
    """
    
    REGISTRATION_MODE_CHOICES = [
        ('SOLO', 'Solo Players Only'),
        ('TEAM', 'Teams Only'),
        ('BOTH', 'Solo & Teams Allowed'),
    ]
    
    tournament = models.OneToOneField(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='capacity',
        primary_key=True
    )
    
    # Capacity
    max_participants = models.PositiveIntegerField(
        help_text="Maximum number of participants (players or teams)"
    )
    min_participants = models.PositiveIntegerField(
        default=2,
        help_text="Minimum needed to start tournament"
    )
    
    # Registration mode
    registration_mode = models.CharField(
        max_length=10,
        choices=REGISTRATION_MODE_CHOICES,
        default='BOTH',
        help_text="Who can register: solo players, teams, or both"
    )
    
    # Team requirements (when registration_mode is TEAM or BOTH)
    required_team_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Exact team size required (e.g., 5 for Valorant)"
    )
    min_team_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Minimum team size allowed"
    )
    max_team_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum team size allowed"
    )
    
    # Waitlist
    enable_waitlist = models.BooleanField(
        default=False,
        help_text="Allow waitlist when full"
    )
    waitlist_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum waitlist size"
    )
    
    # Auto-confirmation
    auto_confirm_registrations = models.BooleanField(
        default=False,
        help_text="Automatically confirm registrations without manual review"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tournament_capacities'
        verbose_name = 'Tournament Capacity'
        verbose_name_plural = 'Tournament Capacities'
    
    def __str__(self):
        return f"Capacity for {self.tournament.name}: {self.max_participants} max"
    
    def clean(self):
        """Validate capacity settings."""
        errors = {}
        
        # Min must be less than max
        if self.min_participants >= self.max_participants:
            errors['min_participants'] = 'Must be less than max participants'
        
        # Team size validation
        if self.registration_mode in ['TEAM', 'BOTH']:
            if self.required_team_size:
                if self.min_team_size and self.required_team_size < self.min_team_size:
                    errors['required_team_size'] = 'Cannot be less than min team size'
                if self.max_team_size and self.required_team_size > self.max_team_size:
                    errors['required_team_size'] = 'Cannot be greater than max team size'
        
        if errors:
            raise ValidationError(errors)
    
    @property
    def current_participants_count(self) -> int:
        """Get current number of confirmed participants."""
        try:
            return self.tournament.registrations.filter(status='CONFIRMED').count()
        except:
            return 0
    
    @property
    def is_full(self) -> bool:
        """Check if tournament is at capacity."""
        return self.current_participants_count >= self.max_participants
    
    @property
    def available_slots(self) -> int:
        """Get number of available slots."""
        return max(0, self.max_participants - self.current_participants_count)
```

Continue in next message...

---

## Step 2: Create Migrations

**After creating all models, generate migrations:**

```bash
python manage.py makemigrations tournaments
```

**Expected migration will:**
1. Create new tables (tournament_schedules, tournament_capacities, etc.)
2. NOT remove old fields (for backward compatibility)

---

## Step 3: Data Migration Script

**Create custom migration to move existing data:**

```python
# apps/tournaments/migrations/XXXX_migrate_to_structured_models.py
from django.db import migrations


def migrate_schedule_data(apps, schema_editor):
    """Move schedule fields to TournamentSchedule."""
    Tournament = apps.get_model('tournaments', 'Tournament')
    TournamentSchedule = apps.get_model('tournaments', 'TournamentSchedule')
    
    for tournament in Tournament.objects.all():
        if not hasattr(tournament, 'schedule'):
            TournamentSchedule.objects.create(
                tournament=tournament,
                registration_opens_at=tournament.reg_open_at,
                registration_closes_at=tournament.reg_close_at,
                tournament_starts_at=tournament.start_at,
                tournament_ends_at=tournament.end_at,
                timezone='Asia/Dhaka'
            )


def migrate_capacity_data(apps, schema_editor):
    """Move capacity fields to TournamentCapacity."""
    Tournament = apps.get_model('tournaments', 'Tournament')
    TournamentCapacity = apps.get_model('tournaments', 'TournamentCapacity')
    
    for tournament in Tournament.objects.all():
        if not hasattr(tournament, 'capacity'):
            # Determine registration mode based on game
            if tournament.game == 'efootball':
                reg_mode = 'SOLO'  # eFootball is 1v1
                team_size = None
            elif tournament.game == 'valorant':
                reg_mode = 'BOTH'  # Valorant supports both
                team_size = 5
            else:
                reg_mode = 'BOTH'
                team_size = None
            
            TournamentCapacity.objects.create(
                tournament=tournament,
                max_participants=tournament.slot_size or 32,
                min_participants=2,
                registration_mode=reg_mode,
                required_team_size=team_size,
                enable_waitlist=False,
                auto_confirm_registrations=False
            )


class Migration(migrations.Migration):
    dependencies = [
        ('tournaments', 'XXXX_previous_migration'),
    ]
    
    operations = [
        migrations.RunPython(migrate_schedule_data),
        migrations.RunPython(migrate_capacity_data),
        # Add more migration functions for other models
    ]
```

---

## Step 4: Update Tournament Model

**Add backward-compatible properties:**

```python
# In apps/tournaments/models/tournament.py

class Tournament(models.Model):
    # ... existing fields ...
    
    # Keep old fields for now (will deprecate later)
    slot_size = models.PositiveIntegerField(null=True, blank=True)  # DEPRECATED
    reg_open_at = models.DateTimeField(blank=True, null=True)  # DEPRECATED
    reg_close_at = models.DateTimeField(blank=True, null=True)  # DEPRECATED
    start_at = models.DateTimeField(blank=True, null=True)  # DEPRECATED
    end_at = models.DateTimeField(blank=True, null=True)  # DEPRECATED
    
    # Backward compatibility properties
    @property
    def reg_open_at_compat(self):
        """Get registration open time (new or old field)."""
        if hasattr(self, 'schedule') and self.schedule:
            return self.schedule.registration_opens_at
        return self.reg_open_at
    
    @property
    def reg_close_at_compat(self):
        """Get registration close time (new or old field)."""
        if hasattr(self, 'schedule') and self.schedule:
            return self.schedule.registration_closes_at
        return self.reg_close_at
    
    @property
    def start_at_compat(self):
        """Get tournament start time (new or old field)."""
        if hasattr(self, 'schedule') and self.schedule:
            return self.schedule.tournament_starts_at
        return self.start_at
    
    @property
    def end_at_compat(self):
        """Get tournament end time (new or old field)."""
        if hasattr(self, 'schedule') and self.schedule:
            return self.schedule.tournament_ends_at
        return self.end_at
    
    @property
    def slot_size_compat(self):
        """Get max participants (new or old field)."""
        if hasattr(self, 'capacity') and self.capacity:
            return self.capacity.max_participants
        return self.slot_size
```

---

## Step 5: Update Admin

**Update TournamentAdmin to use new models:**

```python
# apps/tournaments/admin/tournaments/admin.py

# Add inlines for new models
from apps.tournaments.models.core import (
    TournamentSchedule,
    TournamentCapacity,
    TournamentFinance,
    TournamentMedia,
    TournamentRules
)


class TournamentScheduleInline(admin.StackedInline):
    model = TournamentSchedule
    can_delete = False
    verbose_name = 'Schedule'
    verbose_name_plural = 'Schedule'
    fieldsets = [
        ('Registration Window', {
            'fields': ['registration_opens_at', 'registration_closes_at']
        }),
        ('Tournament Window', {
            'fields': ['tournament_starts_at', 'tournament_ends_at']
        }),
        ('Check-in Window (Optional)', {
            'fields': ['checkin_opens_at', 'checkin_closes_at'],
            'classes': ['collapse']
        }),
        ('Settings', {
            'fields': ['timezone']
        }),
    ]


class TournamentCapacityInline(admin.StackedInline):
    model = TournamentCapacity
    can_delete = False
    verbose_name = 'Capacity & Registration'
    verbose_name_plural = 'Capacity & Registration'
    fieldsets = [
        ('Capacity', {
            'fields': ['max_participants', 'min_participants']
        }),
        ('Registration Mode', {
            'fields': ['registration_mode', 'auto_confirm_registrations']
        }),
        ('Team Settings', {
            'fields': ['required_team_size', 'min_team_size', 'max_team_size'],
            'classes': ['collapse']
        }),
        ('Waitlist', {
            'fields': ['enable_waitlist', 'waitlist_size'],
            'classes': ['collapse']
        }),
    ]


# Add to TournamentAdmin
class TournamentAdmin(...):
    inlines = [
        TournamentScheduleInline,
        TournamentCapacityInline,
        TournamentFinanceInline,  # Create similar inlines
        TournamentMediaInline,
        TournamentRulesInline,
        # ... existing inlines
    ]
```

---

## Step 6: Testing Plan

### A. Unit Tests

```python
# tests/test_structured_models.py

class TournamentScheduleTests(TestCase):
    def test_schedule_creation(self):
        """Test creating a tournament schedule."""
        tournament = Tournament.objects.create(name="Test", game="valorant")
        schedule = TournamentSchedule.objects.create(
            tournament=tournament,
            registration_opens_at=timezone.now(),
            registration_closes_at=timezone.now() + timedelta(days=7),
            tournament_starts_at=timezone.now() + timedelta(days=8),
            tournament_ends_at=timezone.now() + timedelta(days=9)
        )
        self.assertEqual(schedule.tournament, tournament)
    
    def test_schedule_validation(self):
        """Test schedule validation logic."""
        tournament = Tournament.objects.create(name="Test", game="valorant")
        schedule = TournamentSchedule(
            tournament=tournament,
            registration_opens_at=timezone.now() + timedelta(days=7),
            registration_closes_at=timezone.now(),  # Invalid: before opens
            tournament_starts_at=timezone.now() + timedelta(days=8),
            tournament_ends_at=timezone.now() + timedelta(days=9)
        )
        with self.assertRaises(ValidationError):
            schedule.clean()


class TournamentCapacityTests(TestCase):
    def test_capacity_creation(self):
        """Test creating tournament capacity."""
        tournament = Tournament.objects.create(name="Test", game="valorant")
        capacity = TournamentCapacity.objects.create(
            tournament=tournament,
            max_participants=32,
            min_participants=2,
            registration_mode='TEAM',
            required_team_size=5
        )
        self.assertEqual(capacity.max_participants, 32)
    
    def test_is_full_property(self):
        """Test capacity full detection."""
        # ... test logic
```

### B. Integration Tests

```python
def test_backward_compatibility(self):
    """Test that old code still works with new structure."""
    tournament = Tournament.objects.create(
        name="Test",
        game="valorant",
        # Old fields (still work)
        slot_size=32,
        reg_open_at=timezone.now(),
        reg_close_at=timezone.now() + timedelta(days=7),
        start_at=timezone.now() + timedelta(days=8),
        end_at=timezone.now() + timedelta(days=9)
    )
    
    # Create new structured data
    TournamentSchedule.objects.create(...)
    TournamentCapacity.objects.create(...)
    
    # Test that compat properties work
    self.assertIsNotNone(tournament.reg_open_at_compat)
    self.assertIsNotNone(tournament.slot_size_compat)
```

---

## Rollback Plan

**If issues occur:**

1. **Revert migrations:**
   ```bash
   python manage.py migrate tournaments XXXX_previous_migration
   ```

2. **Old fields still exist** - System continues working with old structure

3. **No data loss** - All data remains in original fields

---

## Success Criteria

- [ ] All new models created
- [ ] Migrations run successfully
- [ ] Data migrated to new models
- [ ] Admin shows new inlines
- [ ] Old code still works (backward compatibility)
- [ ] All tests pass
- [ ] No production errors

---

## Timeline

**Week 1:**
- Days 1-2: Create models
- Days 3-4: Write migrations
- Day 5: Test migrations

**Week 2:**
- Days 1-2: Update admin
- Days 3-4: Write tests
- Day 5: Deploy to staging

---

**Ready to start?** Begin with creating `TournamentSchedule` model!
