# New Developer Onboarding Guide - DeltaCrown

**Welcome to DeltaCrown!**  
**Date:** November 2, 2025  
**For:** New developer working on Tournament V2  
**Current State:** Phase 3 Complete - Interface Layer & Decoupling Done

---

## 🎯 Your Mission

You will be designing and building **Tournament System V2** - a clean, modern replacement for the current tournament system. This guide explains:
1. What exists now (V1)
2. How apps communicate
3. The interface you must implement
4. How V2 will coexist with V1
5. Migration strategy

---

## 📚 Essential Reading (In Order)

### Start Here (1-2 hours):
1. **`ARCHITECTURE_STATUS_PHASE3_COMPLETE.md`** ← START HERE!
   - Current architecture state
   - How apps communicate now
   - Frontend, backend, database overview
   - **READ THIS FIRST**

2. **`00_README_START_HERE.md`**
   - Project overview
   - Document roadmap
   - Quick navigation guide

3. **`01_PROJECT_OVERVIEW.md`**
   - 17 Django apps explained
   - Application architecture
   - Database structure
   - URL structure

### Deep Dive (2-4 hours):
4. **`02_CURRENT_TECH_STACK.md`**
   - Django 4.2, PostgreSQL, Redis, Celery
   - All dependencies explained
   - Production considerations

5. **`10_CURRENT_PROBLEMS.md`** (UPDATED with Phase 2 & 3 resolutions)
   - What problems existed
   - ✅ What was fixed in Phase 2 & 3
   - 🔴 What still needs fixing in V2

6. **`06_SIGNAL_SYSTEM_ANALYSIS.md`**
   - How the old signal system worked (historical)
   - Why it was problematic
   - How Phase 2 replaced it with events

### V2 Design Preparation (2-3 hours):
7. **Review Phase 2 & 3 Docs:**
   - `/PHASE_2_COMPLETE.md` - Event-driven architecture
   - `/PHASE_3_PROGRESS.md` - Interface layer details
   - `/MIGRATION_GUIDE_SIGNALS_TO_EVENTS.md` - How migration works

8. **Study the Provider Interface:**
   - File: `apps/core/interfaces/__init__.py`
   - Read: `ITournamentProvider` - 20+ methods you'll implement
   - Read: `IGameConfigProvider` - Game abstraction interface

9. **Study V1 Implementation:**
   - File: `apps/core/providers/tournament_provider_v1.py`
   - See: How V1 wraps current Tournament models
   - Pattern: What you'll do but better in V2

---

## 🏗️ Current Architecture (Phase 3)

### How Apps Access Tournaments Now

```python
# apps/teams/views.py - Example

from apps.core.registry import service_registry

def team_dashboard(request, team_slug):
    # 1. Get provider from registry
    provider = service_registry.get('tournament_provider')
    
    # 2. Use interface methods (doesn't know if V1, V2, or external API)
    tournaments = provider.list_tournaments(status='upcoming', game='valorant')
    
    # 3. Returns results - apps don't care about implementation
    return render(request, 'teams/dashboard.html', {
        'tournaments': tournaments
    })
```

**Key Points:**
- ✅ No direct Tournament imports
- ✅ Apps use `ITournamentProvider` interface
- ✅ Provider implementation swappable
- ✅ V1 and V2 can coexist

### Communication Flow

```
┌─────────────┐
│ Teams App   │─────┐
└─────────────┘     │
                    │
┌─────────────┐     │     ┌────────────────────┐
│Notifications│─────┼────>│  Service Registry   │
└─────────────┘     │     │  get('tournament_   │
                    │     │     provider')      │
┌─────────────┐     │     └────────────────────┘
│  Economy    │─────┘              │
└─────────────┘                    │
                                   ↓
                    ┌──────────────┴──────────────┐
                    │                             │
                    ↓                             ↓
        ┌──────────────────┐        ┌──────────────────┐
        │ Provider V1       │        │ Provider V2      │
        │ (Current System)  │        │ (Your System)    │
        └──────────────────┘        └──────────────────┘
                │                             │
                ↓                             ↓
        ┌──────────────────┐        ┌──────────────────┐
        │Tournament Models │        │Tournament V2     │
        │  (Legacy)        │        │  Models          │
        └──────────────────┘        └──────────────────┘
```

**Feature Flag Controls:**
```python
if feature_flags.is_enabled('tournament_v2', user=request.user):
    provider = service_registry.get('tournament_provider', version='2.0')
else:
    provider = service_registry.get('tournament_provider', version='1.0')
```

---

## 🎯 Your Implementation: ITournamentProvider

### The Interface You Must Implement

**File:** `apps/core/interfaces/__init__.py`

```python
class ITournamentProvider(ABC):
    """Abstract interface for tournament operations"""
    
    # Core Tournament Methods (REQUIRED)
    @abstractmethod
    def get_tournament(self, tournament_id: int) -> Any:
        """Get tournament by ID - return None if not found"""
        pass
    
    @abstractmethod
    def list_tournaments(self, status: Optional[str] = None, 
                        game: Optional[str] = None, 
                        filters: Optional[Dict] = None, 
                        limit: int = 100) -> List[Any]:
        """List tournaments with optional filters"""
        pass
    
    @abstractmethod
    def create_tournament(self, **data) -> Any:
        """Create new tournament"""
        pass
    
    @abstractmethod
    def update_tournament(self, tournament_id: int, **data) -> Any:
        """Update tournament"""
        pass
    
    @abstractmethod
    def delete_tournament(self, tournament_id: int) -> None:
        """Delete tournament"""
        pass
    
    # Registration Methods (REQUIRED)
    @abstractmethod
    def get_registration(self, registration_id: int) -> Any:
        """Get registration by ID"""
        pass
    
    @abstractmethod
    def get_registrations(self, tournament_id: int, 
                         status: Optional[str] = None) -> List[Any]:
        """Get registrations for tournament"""
        pass
    
    @abstractmethod
    def create_registration(self, tournament_id: int, 
                          team_id: Optional[int] = None, 
                          user_id: Optional[int] = None, 
                          **data) -> Any:
        """Create registration"""
        pass
    
    @abstractmethod
    def update_registration_status(self, registration_id: int, 
                                   status: str) -> Any:
        """Update registration status"""
        pass
    
    @abstractmethod
    def delete_registration(self, registration_id: int) -> None:
        """Delete registration"""
        pass
    
    # Match Methods (REQUIRED)
    @abstractmethod
    def get_match(self, match_id: int) -> Any:
        """Get match by ID"""
        pass
    
    @abstractmethod
    def get_tournament_matches(self, tournament_id: int, 
                              round_no: Optional[int] = None) -> List[Any]:
        """Get matches for tournament"""
        pass
    
    @abstractmethod
    def create_match(self, tournament_id: int, **data) -> Any:
        """Create match"""
        pass
    
    @abstractmethod
    def update_match(self, match_id: int, **data) -> Any:
        """Update match"""
        pass
    
    # Payment Methods (REQUIRED)
    @abstractmethod
    def get_payment_verification(self, registration_id: int) -> Any:
        """Get payment verification"""
        pass
    
    @abstractmethod
    def verify_payment(self, registration_id: int, **data) -> Any:
        """Verify payment"""
        pass
    
    # Stats & Analytics (REQUIRED)
    @abstractmethod
    def get_tournament_stats(self, tournament_id: int) -> Dict[str, Any]:
        """Get tournament statistics"""
        pass
    
    @abstractmethod
    def get_participant_count(self, tournament_id: int) -> int:
        """Get participant count"""
        pass
    
    # Settings (REQUIRED)
    @abstractmethod
    def get_tournament_settings(self, tournament_id: int) -> Any:
        """Get tournament settings"""
        pass
    
    @abstractmethod
    def update_tournament_settings(self, tournament_id: int, **data) -> Any:
        """Update tournament settings"""
        pass
```

**Total Methods to Implement:** 20+ methods

---

## 🛠️ Your V2 Implementation Structure

### Step 1: Create Tournament V2 App

```bash
# Create new app
python manage.py startapp tournaments_v2

# Move to apps/
mv tournaments_v2 apps/
```

### Step 2: Design V2 Models

**File:** `apps/tournaments_v2/models/tournament.py`

```python
from django.db import models

class TournamentV2(models.Model):
    """
    V2 Tournament Model - Clean, modern design
    
    Key Improvements over V1:
    - Single source of truth (no duplicate fields)
    - Flexible game support (plugin architecture)
    - Clear configuration (no 8 related models)
    - Proper constraints
    """
    
    # Core fields
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    game = models.CharField(max_length=50)  # Or ForeignKey to Game model
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    # Configuration (JSON for flexibility)
    config = models.JSONField(default=dict, help_text="Tournament configuration")
    rules = models.JSONField(default=dict, help_text="Game rules and settings")
    
    # Schedule
    registration_start = models.DateTimeField()
    registration_end = models.DateTimeField()
    tournament_start = models.DateTimeField()
    tournament_end = models.DateTimeField(null=True)
    
    # Capacity
    max_participants = models.PositiveIntegerField()
    current_participants = models.PositiveIntegerField(default=0)
    
    # Finance
    entry_fee = models.DecimalField(max_digits=10, decimal_places=2)
    prize_pool = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'tournaments_v2'
        indexes = [
            models.Index(fields=['game', 'status']),
            models.Index(fields=['slug']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.game})"
```

**Design Principles:**
- ✅ **Single model** for tournament (not 8 related models)
- ✅ **JSONField** for flexible configuration
- ✅ **Clear constraints** at database level
- ✅ **Proper indexes** for performance
- ✅ **Auditing** (created_at, updated_at, created_by)

### Step 3: Create V2 Provider

**File:** `apps/core/providers/tournament_provider_v2.py`

```python
from apps.core.interfaces import ITournamentProvider
from apps.core.events import event_bus
from apps.core.events.events import TournamentCreatedEvent
from django.apps import apps

class TournamentProviderV2(ITournamentProvider):
    """
    V2 implementation using new tournament models
    
    Improvements:
    - Cleaner data model
    - Better performance
    - More flexible game support
    - Event-driven
    """
    
    def __init__(self):
        self._tournament_model = None
    
    @property
    def Tournament(self):
        if self._tournament_model is None:
            self._tournament_model = apps.get_model('tournaments_v2', 'TournamentV2')
        return self._tournament_model
    
    def get_tournament(self, tournament_id: int):
        """Get tournament by ID"""
        try:
            return self.Tournament.objects.get(id=tournament_id)
        except self.Tournament.DoesNotExist:
            return None
    
    def list_tournaments(self, status=None, game=None, filters=None, limit=100):
        """List tournaments"""
        queryset = self.Tournament.objects.all()
        
        if status:
            queryset = queryset.filter(status=status)
        if game:
            queryset = queryset.filter(game=game)
        if filters:
            queryset = queryset.filter(**filters)
        
        return list(queryset[:limit])
    
    def create_tournament(self, **data):
        """Create tournament and publish event"""
        tournament = self.Tournament.objects.create(**data)
        
        # Publish event
        event_bus.publish(TournamentCreatedEvent(
            tournament_id=tournament.id,
            game=tournament.game,
            created_by=data.get('created_by_id')
        ))
        
        return tournament
    
    # ... implement all other interface methods
```

### Step 4: Register V2 Provider

**File:** `apps/core/apps.py`

```python
def ready(self):
    from .providers import tournament_provider_v1, tournament_provider_v2
    
    # Register both V1 and V2
    service_registry.register('tournament_provider', tournament_provider_v1, version='1.0')
    service_registry.register('tournament_provider', tournament_provider_v2, version='2.0')
```

### Step 5: Feature Flag System

**File:** `apps/core/feature_flags.py`

```python
class FeatureFlags:
    """Simple feature flag system"""
    
    def is_enabled(self, flag_name, user=None, tournament_id=None):
        """Check if feature is enabled"""
        if flag_name == 'tournament_v2':
            # Gradual rollout logic
            if tournament_id:
                # 10% of tournaments use V2
                return tournament_id % 10 == 0
            if user and user.is_staff:
                # Staff always gets V2
                return True
            return False
        return False

feature_flags = FeatureFlags()
```

---

## 📋 V2 Design Requirements

### Must-Haves (Non-Negotiable)

1. **Implements ITournamentProvider** ✅ Required
   - All 20+ methods implemented
   - Same signatures as V1
   - Returns same data structures

2. **Event-Driven** ✅ Required
   - Publishes events for all state changes
   - Uses existing event_bus
   - No signals (use events instead)

3. **Database Migration** ✅ Required
   - Data migration plan from V1 → V2
   - Backward compatibility during transition
   - Rollback strategy

4. **Zero Breaking Changes** ✅ Required
   - Apps don't need to change code
   - Same interface as V1
   - Can run V1 and V2 simultaneously

5. **Performance** ✅ Required
   - Faster than V1 (benchmarks required)
   - Optimized queries (select_related, prefetch_related)
   - Database indexes

### Nice-to-Haves (Recommended)

1. **Flexible Game Support**
   - Plugin architecture for games
   - Easy to add new games without code changes
   - Game configs in database, not hardcoded

2. **Unified Configuration**
   - Single source of truth for tournament config
   - No 8 related models
   - Clear, documented structure

3. **Better Admin Interface**
   - Single-page tournament creation
   - Unified workflow for verifications
   - Dashboard for organizers

4. **API-First Design**
   - RESTful API for all operations
   - GraphQL option (future)
   - Versioned endpoints

5. **Audit Trail**
   - Track all changes
   - Who did what when
   - Rollback capability

---

## 🧪 Testing Strategy

### Required Tests

1. **Unit Tests** - Each provider method
```python
def test_get_tournament():
    provider = TournamentProviderV2()
    tournament = provider.get_tournament(1)
    assert tournament is not None
```

2. **Integration Tests** - Interface compliance
```python
def test_v2_implements_interface():
    """Verify V2 implements all required methods"""
    provider = TournamentProviderV2()
    
    required_methods = [
        'get_tournament', 'list_tournaments', 'create_tournament',
        # ... all interface methods
    ]
    
    for method in required_methods:
        assert hasattr(provider, method)
        assert callable(getattr(provider, method))
```

3. **Compatibility Tests** - V1 and V2 parity
```python
def test_v1_v2_compatibility():
    """V1 and V2 should return same data structure"""
    v1_provider = service_registry.get('tournament_provider', version='1.0')
    v2_provider = service_registry.get('tournament_provider', version='2.0')
    
    v1_result = v1_provider.list_tournaments(game='valorant')
    v2_result = v2_provider.list_tournaments(game='valorant')
    
    # Same structure, may have different implementations
    assert len(v1_result) == len(v2_result)
```

4. **Performance Tests** - V2 must be faster
```python
import time

def test_v2_performance():
    """V2 should be faster than V1"""
    v1_provider = service_registry.get('tournament_provider', version='1.0')
    v2_provider = service_registry.get('tournament_provider', version='2.0')
    
    # Time V1
    start = time.time()
    v1_provider.list_tournaments(limit=100)
    v1_time = time.time() - start
    
    # Time V2
    start = time.time()
    v2_provider.list_tournaments(limit=100)
    v2_time = time.time() - start
    
    assert v2_time < v1_time, f"V2 slower: {v2_time}s vs V1: {v1_time}s"
```

---

## 🔄 Migration Strategy

### Phase 1: Development (2-3 weeks)
```
Week 1: Design V2 models, create migrations
Week 2: Implement TournamentProviderV2
Week 3: Unit tests, integration tests
```

### Phase 2: Testing (1-2 weeks)
```
Week 4: Deploy to staging, test with real data
Week 5: Performance testing, bug fixes
```

### Phase 3: Gradual Rollout (2-3 weeks)
```
Week 6: Enable for staff users only (0.1% traffic)
Week 7: Enable for 10% of tournaments
Week 8: Enable for 50% of tournaments
Week 9: Enable for 100% of tournaments
```

### Phase 4: Data Migration (1 week)
```
Week 10: Migrate all V1 data to V2 format
        Run both systems in parallel
        Verify data consistency
```

### Phase 5: Cleanup (1 week)
```
Week 11: Remove V1 provider
        Remove V1 models (after backup)
        Update documentation
```

**Total Timeline:** 11 weeks (3 months)

---

## 🚀 Getting Started Checklist

### Week 1: Onboarding
- [ ] Read all documentation in `/Documents/For_New_Tournament_design/`
- [ ] Read `ARCHITECTURE_STATUS_PHASE3_COMPLETE.md`
- [ ] Study `ITournamentProvider` interface
- [ ] Review `TournamentProviderV1` implementation
- [ ] Run existing tests: `pytest tests/test_phase3_integration.py`
- [ ] Set up local development environment

### Week 2: Design
- [ ] Design V2 database schema (ERD diagram)
- [ ] Design game plugin architecture
- [ ] Design unified configuration structure
- [ ] Review design with team
- [ ] Get approval on architecture

### Week 3: Implementation Start
- [ ] Create `tournaments_v2` app
- [ ] Create V2 models
- [ ] Create migrations
- [ ] Start implementing `TournamentProviderV2`

---

## 📞 Questions & Support

### Common Questions

**Q: Do I need to modify existing apps?**  
A: **No!** Apps use ITournamentProvider interface. They don't care if it's V1 or V2.

**Q: Can V1 and V2 run together?**  
A: **Yes!** Feature flags control which provider is used. Both can coexist.

**Q: What if I need to add a new method?**  
A: Add it to `ITournamentProvider` interface, implement in both V1 and V2.

**Q: How do I test without breaking V1?**  
A: V2 has separate database tables (`tournaments_v2` prefix). Won't affect V1.

**Q: What about existing tournaments?**  
A: V1 continues serving existing tournaments. New tournaments can use V2.

---

## 🎯 Success Criteria

Your V2 implementation is successful when:

1. ✅ **All interface methods implemented** (20+ methods)
2. ✅ **Integration tests passing** (17+ tests)
3. ✅ **Apps work with both V1 and V2** (no code changes)
4. ✅ **Performance better than V1** (benchmark tests)
5. ✅ **Feature flags working** (gradual rollout)
6. ✅ **Data migration successful** (V1 → V2 without data loss)
7. ✅ **Zero downtime deployment** (both systems coexist)
8. ✅ **Documentation complete** (architecture, API, migration)

---

## 📚 Additional Resources

- **Django ORM:** https://docs.djangoproject.com/en/4.2/topics/db/
- **PostgreSQL:** https://www.postgresql.org/docs/
- **Celery:** https://docs.celeryproject.org/
- **Redis:** https://redis.io/docs/
- **Testing:** https://docs.pytest.org/

---

**Good luck building Tournament V2!** 🚀

**Questions?** Review existing code, read documentation, experiment in staging.

**Remember:** You're not alone. The interface is already defined, V1 is reference implementation, and apps are already decoupled. You're building a better implementation of an existing contract.
