# Complete DeltaCrown Architecture Roadmap

## Overview

**Total Phases: 5 phases**
**Current Status: Phase 2 (35% complete)**
**Estimated Total Time: 6-8 weeks**

---

## Phase 1: Core Infrastructure ✅ COMPLETE (Week 1)

### What We Built
- ✅ Event Bus System (261 lines)
- ✅ Service Registry (180 lines)
- ✅ Plugin Framework (220 lines)
- ✅ API Gateway (150 lines)
- ✅ 23/23 tests passing (100% coverage)

**Status:** ✅ Production ready
**Time Taken:** ~1 week

---

## Phase 2: Signal Migration 🚧 IN PROGRESS (Weeks 2-3)

### Goal
Replace Django's hidden signal handlers with explicit event-driven architecture.

### Current Progress: 35% Complete

#### ✅ Completed
- Tournaments: 5/11 handlers (45%)
- Notifications: 3/3 handlers (100%)
- Service layer for tournaments (3 services)

#### 🔲 Remaining
- **Teams: 0/13 handlers** ← NEXT (2-3 hours)
- **Economy: 0/1 handler** (30 minutes)
- **Other apps: 0/9 handlers** (2-3 hours)
- **View migration:** Update views to use service layer (4-6 hours)
- **Cleanup:** Remove legacy signals after testing (1-2 hours)

### Sub-Phases

#### Phase 2.1: Event Handler Migration (Week 2)
- [x] Tournaments app event handlers
- [x] Notifications app event handlers
- [ ] **Teams app event handlers** ← YOU ARE HERE
- [ ] Economy app event handlers
- [ ] Other apps (user_profile, siteui, accounts)

**Estimated:** 5-8 hours remaining

#### Phase 2.2: Service Layer Adoption (Week 3)
- [ ] Update tournament views to use TournamentService
- [ ] Update team views to use TeamService
- [ ] Update registration flows to use RegistrationService
- [ ] Integration testing

**Estimated:** 8-12 hours

#### Phase 2.3: Legacy Removal (Week 3 end)
- [ ] Verify both systems behave identically
- [ ] Feature flag to switch between systems
- [ ] Gradual rollout to production
- [ ] Remove old signal handlers
- [ ] Archive signal.py files

**Estimated:** 4-6 hours

**Phase 2 Total Estimate:** 2-3 weeks

---

## Phase 3: Decoupling & Interfaces 📋 PLANNED (Weeks 4-5)

### Goal
Create clean interfaces so apps don't depend on tournaments/games directly.

### What Needs to Be Done

#### 3.1: Tournament Interface (Week 4)
```python
# Create abstract tournament interface
class ITournamentProvider:
    def get_tournament(self, id: int) -> Tournament
    def list_tournaments(self, filters: dict) -> List[Tournament]
    def register_participant(self, tournament_id: int, participant)
    def get_registrations(self, tournament_id: int)
    # etc.
```

#### 3.2: Game Config Interface (Week 4)
```python
# Create abstract game config interface
class IGameConfigProvider:
    def get_config(self, game: str, tournament_id: int) -> GameConfig
    def validate_config(self, config: dict) -> bool
    def get_game_specific_rules(self, game: str) -> dict
    # etc.
```

#### 3.3: Refactor Dependencies (Week 5)
- [ ] Teams app uses ITournamentProvider instead of importing Tournament model
- [ ] Notifications uses ITournamentProvider
- [ ] Economy uses ITournamentProvider
- [ ] User profile uses ITournamentProvider
- [ ] Dashboard uses ITournamentProvider

#### 3.4: Plugin Architecture (Week 5)
```python
# Register tournament provider as plugin
registry.register(
    'tournament_provider',
    TournamentProviderV1,  # Current implementation
    version='1.0'
)

# Other apps use:
provider = registry.get('tournament_provider')
tournament = provider.get_tournament(123)
```

**Benefits:**
- ✅ Teams app doesn't import from tournaments
- ✅ Notifications don't import from tournaments
- ✅ Can swap tournament implementation without breaking other apps
- ✅ Can test with mock providers

**Phase 3 Total Estimate:** 2 weeks

---

## Phase 4: New Tournament System 🎯 PLANNED (Weeks 6-7)

### Goal
Build new tournament system without affecting existing apps.

### Approach: Side-by-Side Development

#### 4.1: New Tournament App (Week 6)
```
apps/
  tournaments_v2/          ← NEW APP
    models/
      tournament.py        ← Clean schema
      registration.py
      bracket.py
    services/
      tournament_service.py
    api/
      endpoints.py
```

#### 4.2: New Game Apps (Week 6)
```
apps/
  games/                   ← NEW UNIFIED APP
    valorant/
      config.py
      validators.py
      rules.py
    efootball/
      config.py
      validators.py
      rules.py
    common/
      base_config.py
      interfaces.py
```

#### 4.3: Implement Provider Interface (Week 7)
```python
# New implementation
class TournamentProviderV2(ITournamentProvider):
    """Uses tournaments_v2 models"""
    def get_tournament(self, id: int):
        return TournamentV2.objects.get(id=id)
    # etc.

# Register as alternative provider
registry.register(
    'tournament_provider',
    TournamentProviderV2,
    version='2.0'
)
```

#### 4.4: Feature Flag System (Week 7)
```python
# Use feature flags to toggle between v1 and v2
if feature_flags.is_enabled('tournaments_v2'):
    provider = registry.get('tournament_provider', version='2.0')
else:
    provider = registry.get('tournament_provider', version='1.0')
```

**Phase 4 Total Estimate:** 2 weeks

---

## Phase 5: Migration & Cleanup 🧹 PLANNED (Week 8)

### Goal
Migrate data and remove old apps.

#### 5.1: Data Migration (Week 8)
- [ ] Write migration scripts (tournaments v1 → v2)
- [ ] Write migration scripts (game configs v1 → v2)
- [ ] Test migration on copy of production database
- [ ] Verify data integrity

#### 5.2: Gradual Rollout (Week 8)
- [ ] Enable v2 for 10% of users
- [ ] Monitor errors and performance
- [ ] Enable v2 for 50% of users
- [ ] Enable v2 for 100% of users

#### 5.3: Cleanup (Week 8)
- [ ] Remove old tournament app
- [ ] Remove old game apps (game_valorant, game_efootball)
- [ ] Remove v1 provider implementations
- [ ] Archive old code
- [ ] Update documentation

**Phase 5 Total Estimate:** 1 week

---

## Critical Question: When Can We Replace Tournament Apps?

### Answer: After Phase 3 (Week 5)

**Timeline:**
```
Week 1: ✅ Phase 1 complete
Week 2-3: 🚧 Phase 2 (signal migration) ← YOU ARE HERE
Week 4-5: Phase 3 (decoupling via interfaces)
Week 6+: Phase 4 (can start building new tournament system)
```

### Why Wait Until After Phase 3?

**Current State (BAD):**
```python
# teams/views.py
from apps.tournaments.models import Tournament  # Direct dependency!

def team_view(request):
    tournament = Tournament.objects.get(id=123)  # Breaks if we remove tournaments app!
```

**After Phase 3 (GOOD):**
```python
# teams/views.py
from apps.core.registry import registry  # No direct dependency!

def team_view(request):
    provider = registry.get('tournament_provider')
    tournament = provider.get_tournament(123)  # Works with v1 OR v2!
```

### Safe Replacement Strategy

#### Step 1: Complete Phase 2 (Week 2-3)
- All event handlers migrated
- Service layer in use
- Clean separation of concerns

#### Step 2: Complete Phase 3 (Week 4-5)
- All apps use interfaces (ITournamentProvider)
- No direct imports of Tournament model
- Plugin architecture in place

#### Step 3: Build New System (Week 6-7)
- Create tournaments_v2 app
- Implement ITournamentProvider with v2 models
- Register as alternative provider
- **Old system still works! Nothing breaks!**

#### Step 4: Switch Over (Week 8)
- Use feature flags to toggle between v1/v2
- Migrate data gradually
- Remove old apps once verified

### Dependencies to Remove

**Current Dependencies (These Must Be Eliminated):**

```bash
# Apps that import from tournaments:
apps/teams/           → Tournament, Registration
apps/notifications/   → Tournament, Match, Registration
apps/economy/         → Registration, PaymentVerification
apps/user_profile/    → Tournament, Registration
apps/dashboard/       → Tournament, Match
apps/search/          → Tournament
```

**Phase 3 will remove ALL these direct imports!**

---

## Summary

### Total Timeline: 8 weeks

- ✅ **Week 1:** Phase 1 - Core Infrastructure (DONE)
- 🚧 **Week 2-3:** Phase 2 - Signal Migration (35% DONE)
- 📋 **Week 4-5:** Phase 3 - Decoupling (CRITICAL - enables replacement)
- 🎯 **Week 6-7:** Phase 4 - New System (side-by-side)
- 🧹 **Week 8:** Phase 5 - Migration & Cleanup

### Answer to Your Questions

**Q: How many phases?**
**A:** 5 phases total

**Q: When can we replace tournament/games apps?**
**A:** After Phase 3 (Week 5) - but can START building replacement in Week 6

**Q: Will it break other apps?**
**A:** NO - if we complete Phase 3 first (interface layer)
- Phase 3 removes all direct dependencies
- Other apps use interfaces, not models
- Can swap implementations without breaking anything

### Current Priority

**Complete Phase 2 first!** This is the foundation:
1. ✅ Tournaments (45% done)
2. ✅ Notifications (100% done)
3. **→ Teams (next - 2-3 hours)** ← DO THIS NOW
4. → Economy (30 minutes)
5. → View migration (4-6 hours)
6. → Cleanup (1-2 hours)

**Then move to Phase 3** (the critical decoupling phase)

---

## Risk Assessment

### High Risk (Must Complete Before Replacement)
- ⚠️ Phase 3 incomplete → Other apps break when tournaments removed
- ⚠️ Data migration untested → Data loss

### Medium Risk (Should Complete)
- ⚠️ Phase 2 incomplete → Some event handlers missing, silent failures
- ⚠️ No feature flags → Can't roll back if issues found

### Low Risk (Nice to Have)
- Phase 1 extensions (more plugins)
- Performance optimizations
- Additional testing

---

**NEXT ACTION: Continue Phase 2 by migrating Teams app (13 handlers)**
