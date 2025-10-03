# 🔄 Tournament System - Complete Refactoring Plan

**Date:** October 3, 2025  
**Status:** 📋 Planning Phase  
**Priority:** 🔴 High - Architectural Improvements

---

## Executive Summary

The current tournament system has grown organically and now suffers from several architectural issues:

1. **Poor Organization** - Fields scattered across models, unclear structure
2. **Inconsistent Naming** - Non-professional file/field names
3. **Rigid Registration** - Not dynamic based on game type (team size, solo/team modes)
4. **Incomplete Archiving** - Missing critical data (banners, participants, match results)
5. **Game Logic Separation** - Game-specific logic mixed with core tournament logic

This document outlines a comprehensive refactoring plan to address these issues while maintaining backward compatibility.

---

## Current Issues Analysis

### 1. **Tournament Model Organization** ❌

**Problems:**
- Fields are flat and unstructured
- Game-specific settings mixed with core tournament data
- Unclear field grouping (what's required vs optional?)
- Finance, schedule, and config fields all at same level

**Example of Current Chaos:**
```python
class Tournament(models.Model):
    name = ...                    # Basic
    slug = ...                    # Basic
    game = ...                    # Core config
    status = ...                  # Core config
    banner = ...                  # Media
    slot_size = ...               # Capacity
    reg_open_at = ...            # Schedule
    reg_close_at = ...           # Schedule
    start_at = ...               # Schedule
    end_at = ...                 # Schedule
    entry_fee_bdt = ...          # Finance
    prize_pool_bdt = ...         # Finance
    groups_published = ...       # Publishing
    # ... all mixed together!
```

### 2. **File Naming Issues** ❌

**Non-Professional Names:**
```
forms_registration.py           → ❌ Should be: registration_forms.py
tournament_settings.py          → ✅ OK
paths.py                        → ❌ Vague, should be: media_paths.py
state_machine.py                → ✅ OK
captain_approval.py             → ✅ OK
payment_verification.py         → ✅ OK
```

**Inconsistent Structure:**
- Some models in single files, others grouped
- Mixed concerns in same files
- No clear module boundaries

### 3. **Registration System Issues** ❌

**Current Problems:**

#### A. Not Game-Aware
```python
# Current: Generic registration
class Registration(models.Model):
    user = models.ForeignKey(...)  # For solo
    team = models.ForeignKey(...)  # For team
    # But doesn't check if game supports solo/team!
```

**Should be:**
- Valorant: 5v5 teams OR solo (auto-team formation)
- eFootball: 1v1 only (solo players)
- Each game has different player counts

#### B. Static Registration Forms
```python
# Current: Forms don't adapt to game
class SoloRegistrationForm(...)
class TeamRegistrationForm(...)
# No validation for game-specific team sizes!
```

**Should be:**
- Dynamic forms based on tournament.game
- Validate team size matches game requirements
- Show/hide fields based on game type
- Different workflows per game

#### C. No Team Size Validation
```python
# Valorant team should be 5 players
# eFootball should reject teams (1v1 only)
# But no validation exists!
```

### 4. **Archive System Issues** ❌

**Current State:**
```python
# When status = COMPLETED:
# ✅ Tournament data saved
# ✅ Fields become readonly
# ❌ No banner backup
# ❌ No participant export
# ❌ No match results export
# ❌ No statistics snapshot
# ❌ No bracket export
```

**Missing Archives:**
1. **Banner Images** - Lost if deleted from media
2. **Participants List** - No CSV/JSON export
3. **Match Results** - No comprehensive export
4. **Tournament Stats** - No summary snapshot
5. **Bracket Structure** - No visual export
6. **Payment Records** - No financial archive
7. **Timeline** - No event log

### 5. **Game Logic Mixing** ❌

**Current:**
```python
# Game configs in separate models (good)
class ValorantConfig(models.Model): ...
class EfootballConfig(models.Model): ...

# But game logic scattered everywhere:
# - Registration doesn't check game
# - Forms don't adapt to game
# - Validation doesn't consider game
# - Admin doesn't group by game features
```

---

## Proposed Solution Architecture

### Phase 1: Model Reorganization ⚡

#### A. Introduce Structured Field Groups

**New Approach: Use JSON fields or related models for grouping**

```python
class Tournament(models.Model):
    """Core tournament model - basics only."""
    
    # === CORE IDENTITY ===
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    game = models.CharField(max_length=20, choices=Game.choices)
    
    # === STATUS & LIFECYCLE ===
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)  # When completed
    
    # === ORGANIZER ===
    organizer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='organized_tournaments')
    organizer_team = models.ForeignKey('teams.Team', null=True, blank=True, on_delete=models.SET_NULL)
    
    # === RELATED DATA (moved to separate models) ===
    # TournamentSchedule (1-to-1)
    # TournamentCapacity (1-to-1)
    # TournamentFinance (1-to-1)
    # TournamentMedia (1-to-1)
    # TournamentRules (1-to-1)
    # TournamentArchive (1-to-1, created when COMPLETED)
```

#### B. Create Structured Related Models

**1. Tournament Schedule** (Separate model)
```python
class TournamentSchedule(models.Model):
    """All date/time related fields."""
    tournament = models.OneToOneField(Tournament, on_delete=models.CASCADE, related_name='schedule')
    
    # Registration window
    registration_opens_at = models.DateTimeField()
    registration_closes_at = models.DateTimeField()
    
    # Check-in window
    checkin_opens_at = models.DateTimeField(null=True, blank=True)
    checkin_closes_at = models.DateTimeField(null=True, blank=True)
    
    # Tournament window
    tournament_starts_at = models.DateTimeField()
    tournament_ends_at = models.DateTimeField()
    
    # Timezone
    timezone = models.CharField(max_length=50, default='Asia/Dhaka')
    
    class Meta:
        db_table = 'tournament_schedules'
```

**2. Tournament Capacity** (Separate model)
```python
class TournamentCapacity(models.Model):
    """Participant limits and registration settings."""
    tournament = models.OneToOneField(Tournament, on_delete=models.CASCADE, related_name='capacity')
    
    # Capacity
    max_participants = models.PositiveIntegerField()  # Clear name, not "slot_size"
    min_participants = models.PositiveIntegerField(default=2)
    
    # Registration mode
    REGISTRATION_MODE_CHOICES = [
        ('SOLO', 'Solo Players'),
        ('TEAM', 'Teams Only'),
        ('BOTH', 'Solo & Teams'),
    ]
    registration_mode = models.CharField(max_length=10, choices=REGISTRATION_MODE_CHOICES)
    
    # Team requirements (if TEAM or BOTH)
    required_team_size = models.PositiveIntegerField(null=True, blank=True)  # e.g., 5 for Valorant
    min_team_size = models.PositiveIntegerField(null=True, blank=True)
    max_team_size = models.PositiveIntegerField(null=True, blank=True)
    
    # Waitlist
    enable_waitlist = models.BooleanField(default=False)
    waitlist_size = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'tournament_capacities'
```

**3. Tournament Finance** (Separate model)
```python
class TournamentFinance(models.Model):
    """Entry fees, prizes, payment info."""
    tournament = models.OneToOneField(Tournament, on_delete=models.CASCADE, related_name='finance')
    
    # Entry fee
    has_entry_fee = models.BooleanField(default=False)
    entry_fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    entry_fee_currency = models.CharField(max_length=3, default='BDT')
    
    # Prize pool
    total_prize_pool = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    prize_distribution = models.JSONField(default=dict)  # {1: 50%, 2: 30%, 3: 20%}
    
    # Payment methods
    accepted_payment_methods = models.JSONField(default=list)  # ['bkash', 'nagad', 'rocket']
    payment_instructions = models.TextField(blank=True)
    
    # Payment account details
    payment_accounts = models.JSONField(default=dict)  # {'bkash': '01712345678', ...}
    
    class Meta:
        db_table = 'tournament_finances'
```

**4. Tournament Media** (Separate model)
```python
class TournamentMedia(models.Model):
    """Images, videos, and visual assets."""
    tournament = models.OneToOneField(Tournament, on_delete=models.CASCADE, related_name='media')
    
    # Images
    banner_image = models.ImageField(upload_to='tournaments/banners/', null=True, blank=True)
    thumbnail_image = models.ImageField(upload_to='tournaments/thumbnails/', null=True, blank=True)
    logo_image = models.ImageField(upload_to='tournaments/logos/', null=True, blank=True)
    
    # Image backups (for archive)
    banner_image_backup = models.ImageField(upload_to='tournaments/archives/banners/', null=True, blank=True)
    
    # Videos/Streams
    trailer_video_url = models.URLField(blank=True)
    stream_url = models.URLField(blank=True)
    vod_url = models.URLField(blank=True)
    
    # Social
    social_media_image = models.ImageField(upload_to='tournaments/social/', null=True, blank=True)
    
    class Meta:
        db_table = 'tournament_media'
```

**5. Tournament Rules** (Separate model)
```python
class TournamentRules(models.Model):
    """Rules, format, and game-specific settings."""
    tournament = models.OneToOneField(Tournament, on_delete=models.CASCADE, related_name='rules')
    
    # Format
    BRACKET_TYPE_CHOICES = [
        ('SINGLE_ELIM', 'Single Elimination'),
        ('DOUBLE_ELIM', 'Double Elimination'),
        ('ROUND_ROBIN', 'Round Robin'),
        ('SWISS', 'Swiss System'),
    ]
    bracket_type = models.CharField(max_length=20, choices=BRACKET_TYPE_CHOICES)
    
    # Match format
    best_of = models.PositiveIntegerField(default=1)  # BO1, BO3, BO5
    
    # Rules text
    full_rules = models.TextField(blank=True)
    short_description = models.TextField(blank=True)
    
    # PDF
    rules_pdf = models.FileField(upload_to='tournaments/rules/', null=True, blank=True)
    
    # Conduct
    code_of_conduct_url = models.URLField(blank=True)
    
    class Meta:
        db_table = 'tournament_rules'
```

**6. Tournament Archive** ⚡ **(NEW - Critical)**
```python
class TournamentArchive(models.Model):
    """Complete tournament archive when COMPLETED."""
    tournament = models.OneToOneField(Tournament, on_delete=models.CASCADE, related_name='archive')
    
    # Archive metadata
    archived_at = models.DateTimeField(auto_now_add=True)
    archived_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Snapshot data (JSON)
    tournament_snapshot = models.JSONField()  # All tournament fields at completion
    schedule_snapshot = models.JSONField()
    capacity_snapshot = models.JSONField()
    finance_snapshot = models.JSONField()
    rules_snapshot = models.JSONField()
    
    # Participant exports
    participants_json = models.JSONField()  # All registrations
    participants_csv = models.FileField(upload_to='tournaments/archives/participants/')
    
    # Match results
    matches_json = models.JSONField()  # All match results
    matches_csv = models.FileField(upload_to='tournaments/archives/matches/')
    bracket_json = models.JSONField()  # Complete bracket structure
    
    # Statistics
    statistics_json = models.JSONField()  # Aggregate stats
    
    # Media backups
    banner_backup = models.ImageField(upload_to='tournaments/archives/banners/')
    thumbnail_backup = models.ImageField(upload_to='tournaments/archives/thumbnails/')
    
    # Payment records
    payments_json = models.JSONField()  # All payment records
    payments_csv = models.FileField(upload_to='tournaments/archives/payments/')
    
    # Final standings
    final_standings_json = models.JSONField()
    final_standings_pdf = models.FileField(upload_to='tournaments/archives/standings/', null=True, blank=True)
    
    # Prize distribution record
    prize_distribution_record = models.JSONField()  # Who got what
    
    class Meta:
        db_table = 'tournament_archives'
        indexes = [
            models.Index(fields=['archived_at']),
        ]
```

### Phase 2: Game-Aware Registration System ⚡

#### A. Game Configuration Registry

**Create centralized game config:**
```python
# apps/tournaments/game_configs.py
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class GameConfig:
    """Configuration for a specific game."""
    game_id: str
    game_name: str
    
    # Team settings
    supports_solo: bool
    supports_teams: bool
    required_team_size: Optional[int]
    min_team_size: Optional[int]
    max_team_size: Optional[int]
    
    # Match settings
    default_best_of: int
    default_bracket_type: str
    
    # Specific features
    has_agent_selection: bool  # Valorant
    has_platform_selection: bool  # eFootball (iOS/Android)
    
    # Validation rules
    validation_rules: dict


GAME_CONFIGS = {
    'valorant': GameConfig(
        game_id='valorant',
        game_name='Valorant',
        supports_solo=True,
        supports_teams=True,
        required_team_size=5,
        min_team_size=5,
        max_team_size=5,
        default_best_of=3,
        default_bracket_type='SINGLE_ELIM',
        has_agent_selection=True,
        has_platform_selection=False,
        validation_rules={
            'team_name_required': True,
            'discord_required': True,
            'team_logo_optional': True,
        }
    ),
    'efootball': GameConfig(
        game_id='efootball',
        game_name='eFootball Mobile',
        supports_solo=True,
        supports_teams=False,  # 1v1 only
        required_team_size=None,
        min_team_size=None,
        max_team_size=None,
        default_best_of=1,
        default_bracket_type='SINGLE_ELIM',
        has_agent_selection=False,
        has_platform_selection=True,  # iOS/Android
        validation_rules={
            'platform_required': True,
            'game_id_required': True,
        }
    ),
}

def get_game_config(game_id: str) -> GameConfig:
    """Get configuration for a game."""
    return GAME_CONFIGS.get(game_id)
```

#### B. Dynamic Registration Forms

**Create form factory:**
```python
# apps/tournaments/forms/registration_factory.py

class RegistrationFormFactory:
    """Creates appropriate registration form based on game."""
    
    @staticmethod
    def create_form(tournament: Tournament, user_profile, team=None):
        """Create appropriate form for tournament's game."""
        game_config = get_game_config(tournament.game)
        
        # Determine form type
        if team:
            # Team registration
            if not game_config.supports_teams:
                raise ValueError(f"{game_config.game_name} doesn't support team registration")
            return TeamRegistrationForm(
                tournament=tournament,
                user_profile=user_profile,
                team=team,
                game_config=game_config
            )
        else:
            # Solo registration
            if not game_config.supports_solo:
                raise ValueError(f"{game_config.game_name} requires team registration")
            return SoloRegistrationForm(
                tournament=tournament,
                user_profile=user_profile,
                game_config=game_config
            )
```

**Enhanced Registration Form:**
```python
class DynamicRegistrationForm(forms.Form):
    """Base form that adapts to game requirements."""
    
    def __init__(self, tournament, user_profile, game_config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tournament = tournament
        self.user_profile = user_profile
        self.game_config = game_config
        
        # Add game-specific fields
        self._add_game_specific_fields()
        
        # Add payment fields if needed
        if tournament.finance.has_entry_fee:
            self._add_payment_fields()
    
    def _add_game_specific_fields(self):
        """Add fields based on game."""
        if self.game_config.has_platform_selection:
            self.fields['platform'] = forms.ChoiceField(
                choices=[('ios', 'iOS'), ('android', 'Android')],
                required=True
            )
        
        if self.game_config.has_agent_selection:
            self.fields['preferred_agents'] = forms.MultipleChoiceField(
                # ... agent choices
                required=False
            )
    
    def clean(self):
        data = super().clean()
        
        # Game-specific validation
        if self.game_config.game_id == 'valorant':
            # Valorant-specific validation
            pass
        elif self.game_config.game_id == 'efootball':
            # eFootball-specific validation
            pass
        
        return data
```

### Phase 3: Professional File Renaming

**Proposed Restructure:**
```
apps/tournaments/
├── models/
│   ├── core/
│   │   ├── tournament.py          # Main tournament model
│   │   ├── schedule.py            # TournamentSchedule
│   │   ├── capacity.py            # TournamentCapacity
│   │   ├── finance.py             # TournamentFinance
│   │   ├── media.py               # TournamentMedia
│   │   ├── rules.py               # TournamentRules
│   │   └── archive.py             # TournamentArchive ⚡
│   ├── registration/
│   │   ├── registration.py        # Registration model
│   │   ├── registration_request.py
│   │   └── captain_approval.py
│   ├── matches/
│   │   ├── match.py
│   │   ├── match_attendance.py
│   │   ├── match_dispute.py
│   │   ├── match_event.py
│   │   └── match_comment.py
│   ├── game_configs/
│   │   ├── valorant_config.py
│   │   └── efootball_config.py
│   └── __init__.py
├── forms/
│   ├── registration_forms.py      # Renamed from forms_registration.py
│   ├── match_forms.py
│   └── admin_forms.py
├── services/
│   ├── registration_service.py
│   ├── bracket_service.py
│   ├── match_service.py
│   └── archive_service.py         # ⚡ NEW
├── admin/
│   ├── tournament/
│   │   ├── admin.py
│   │   ├── inlines.py
│   │   ├── mixins.py
│   │   └── filters.py
│   ├── registration/
│   ├── matches/
│   └── payments/
└── views/
    ├── public/
    ├── dashboard/
    └── api/
```

### Phase 4: Complete Archive System ⚡

**Archive Service:**
```python
# apps/tournaments/services/archive_service.py

class TournamentArchiveService:
    """Handles complete tournament archiving."""
    
    @staticmethod
    def archive_tournament(tournament: Tournament, archived_by: User):
        """Create complete archive of tournament."""
        
        # 1. Create archive record
        archive = TournamentArchive.objects.create(
            tournament=tournament,
            archived_by=archived_by
        )
        
        # 2. Snapshot all data
        archive.tournament_snapshot = TournamentArchiveService._snapshot_tournament(tournament)
        archive.schedule_snapshot = TournamentArchiveService._snapshot_schedule(tournament.schedule)
        archive.capacity_snapshot = TournamentArchiveService._snapshot_capacity(tournament.capacity)
        archive.finance_snapshot = TournamentArchiveService._snapshot_finance(tournament.finance)
        archive.rules_snapshot = TournamentArchiveService._snapshot_rules(tournament.rules)
        
        # 3. Export participants
        archive.participants_json = TournamentArchiveService._export_participants_json(tournament)
        archive.participants_csv = TournamentArchiveService._export_participants_csv(tournament)
        
        # 4. Export matches
        archive.matches_json = TournamentArchiveService._export_matches_json(tournament)
        archive.matches_csv = TournamentArchiveService._export_matches_csv(tournament)
        archive.bracket_json = TournamentArchiveService._export_bracket_json(tournament)
        
        # 5. Calculate statistics
        archive.statistics_json = TournamentArchiveService._calculate_statistics(tournament)
        
        # 6. Backup media
        archive.banner_backup = TournamentArchiveService._backup_image(tournament.media.banner_image)
        archive.thumbnail_backup = TournamentArchiveService._backup_image(tournament.media.thumbnail_image)
        
        # 7. Export payments
        archive.payments_json = TournamentArchiveService._export_payments_json(tournament)
        archive.payments_csv = TournamentArchiveService._export_payments_csv(tournament)
        
        # 8. Final standings
        archive.final_standings_json = TournamentArchiveService._export_standings_json(tournament)
        archive.final_standings_pdf = TournamentArchiveService._generate_standings_pdf(tournament)
        
        # 9. Prize distribution
        archive.prize_distribution_record = TournamentArchiveService._record_prize_distribution(tournament)
        
        archive.save()
        
        # 10. Mark tournament as archived
        tournament.archived_at = timezone.now()
        tournament.save()
        
        return archive
    
    @staticmethod
    def _export_participants_csv(tournament):
        """Export participants as CSV file."""
        import csv
        from io import StringIO
        from django.core.files.base import ContentFile
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow([
            'ID', 'Type', 'Name', 'Email', 'Team', 
            'Payment Status', 'Registration Status', 
            'Registered At', 'Payment Verified At'
        ])
        
        # Data
        for reg in tournament.registrations.all():
            writer.writerow([
                reg.id,
                'Solo' if reg.user else 'Team',
                reg.user.display_name if reg.user else reg.team.name,
                reg.user.user.email if reg.user else reg.team.captain.user.email,
                reg.team.tag if reg.team else 'N/A',
                reg.payment_status,
                reg.status,
                reg.created_at.isoformat(),
                reg.payment_verified_at.isoformat() if reg.payment_verified_at else 'N/A'
            ])
        
        # Save to file
        filename = f'tournament_{tournament.id}_participants.csv'
        return ContentFile(output.getvalue().encode('utf-8'), name=filename)
    
    # ... other export methods
```

**Admin Integration:**
```python
# In TournamentAdmin
@admin.action(description="📦 Archive selected tournaments")
def action_archive_tournaments(self, request, queryset):
    """Create complete archives for COMPLETED tournaments."""
    archived = 0
    
    for tournament in queryset:
        if tournament.status != 'COMPLETED':
            self.message_user(
                request,
                f"⚠️ {tournament.name} is not COMPLETED. Only COMPLETED tournaments can be archived.",
                level='warning'
            )
            continue
        
        try:
            # Create archive
            archive = TournamentArchiveService.archive_tournament(
                tournament=tournament,
                archived_by=request.user
            )
            archived += 1
            
            self.message_user(
                request,
                f"✅ {tournament.name} archived successfully!",
                level='success'
            )
        except Exception as e:
            self.message_user(
                request,
                f"❌ Failed to archive {tournament.name}: {e}",
                level='error'
            )
    
    if archived:
        self.message_user(
            request,
            f"📦 {archived} tournament(s) archived successfully!",
            level='success'
        )
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Create new models (Schedule, Capacity, Finance, Media, Rules)
- [ ] Write migration scripts to move existing data
- [ ] Update admin to use new structure
- [ ] Maintain backward compatibility with @property methods

### Phase 2: Game Config System (Week 3)
- [ ] Create GameConfig registry
- [ ] Update Registration model with game validation
- [ ] Create dynamic form factory
- [ ] Update views to use new forms

### Phase 3: File Reorganization (Week 4)
- [ ] Rename and reorganize files
- [ ] Update all imports
- [ ] Update tests
- [ ] Update documentation

### Phase 4: Archive System (Week 5-6)
- [ ] Create TournamentArchive model
- [ ] Implement ArchiveService
- [ ] Add admin actions
- [ ] Create export templates (CSV, PDF)
- [ ] Test with real data

### Phase 5: Testing & Polish (Week 7)
- [ ] Comprehensive testing
- [ ] Performance optimization
- [ ] Documentation update
- [ ] Migration guide for existing tournaments

---

## Backward Compatibility Strategy

**During Transition:**
```python
class Tournament(models.Model):
    # New structured approach
    # schedule → TournamentSchedule (related)
    # capacity → TournamentCapacity (related)
    # finance → TournamentFinance (related)
    
    # Old fields (keep for backward compatibility)
    slot_size = models.PositiveIntegerField(null=True, blank=True)  # Deprecated
    reg_open_at = models.DateTimeField(blank=True, null=True)  # Deprecated
    # ...
    
    # Property wrappers for old code
    @property
    def reg_open_at_compat(self):
        """Backward compatibility: get from schedule if available."""
        if hasattr(self, 'schedule'):
            return self.schedule.registration_opens_at
        return self.reg_open_at  # Fallback to old field
```

---

## Benefits Summary

### 1. **Better Organization** ✅
- Clear separation of concerns
- Structured data models
- Easy to find and modify fields

### 2. **Professional Naming** ✅
- Industry-standard file names
- Clear module boundaries
- Consistent naming conventions

### 3. **Game-Aware Registration** ✅
- Dynamic forms per game
- Proper validation
- Team size enforcement

### 4. **Complete Archives** ✅
- All data preserved
- Multiple export formats
- Media backups
- Financial records

### 5. **Maintainability** ✅
- Easier to add new games
- Clearer code structure
- Better testing capability

---

## Risk Assessment

### High Risk
- **Data Migration** - Moving existing tournament data to new structure
- **Breaking Changes** - Old code dependencies

**Mitigation:**
- Create comprehensive migrations
- Maintain backward compatibility during transition
- Extensive testing before deployment

### Medium Risk
- **Performance** - More database queries with related models
- **Complexity** - More models to manage

**Mitigation:**
- Use select_related() and prefetch_related()
- Optimize queries
- Add database indexes

### Low Risk
- **File renaming** - Import updates needed
- **Admin changes** - UI adjustments

**Mitigation:**
- Automated refactoring tools
- Update documentation
- Gradual rollout

---

## Next Steps

1. **Review & Approve** this plan
2. **Create detailed task breakdown** for Phase 1
3. **Set up feature branch** for refactoring
4. **Begin implementation** starting with model creation
5. **Continuous testing** throughout the process

---

**Status:** 📋 Awaiting Approval  
**Estimated Timeline:** 7 weeks  
**Priority:** High  
**Risk Level:** Medium (with proper planning)

---

**Questions to Answer:**
1. Should we do this refactoring in phases or all at once?
2. Which phase should we prioritize first?
3. Do we need to maintain the old structure indefinitely?
4. Should we create a new Django app or refactor in place?

