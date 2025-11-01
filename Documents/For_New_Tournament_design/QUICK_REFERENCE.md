# Quick Reference - Tournament System Architecture

**Document:** Quick Reference Guide  
**Purpose:** Fast overview for new developers  
**Read Time:** 5 minutes

---

## 🎯 The Big Picture

```
Current State: MVP Tournament System (Working but Problematic)
Problem: Tight coupling, signal hell, configuration chaos
Goal: Redesign to support 50+ games and flexible tournament formats
```

---

## 📊 Current System at a Glance

### Core Stats
- **Main App:** `apps/tournaments/` (~15,000 lines of code)
- **Models:** 20+ tournament-related models
- **Signal Handlers:** 11+ signal handlers (the problem!)
- **Dependencies:** 6 other apps (tight coupling)
- **Supported Games:** 8 games (2 fully integrated: Valorant, eFootball)
- **Test Files:** 94+ test files

### Tech Stack (Essential)
```
Python 3.11
Django 4.2 LTS
PostgreSQL (database: deltacrown, user: dc_user)
Redis (Celery + Channels)
Django REST Framework
CKEditor 5 (rich text)
Celery (async tasks)
Django Channels (WebSockets)
```

---

## 🏗️ Application Architecture

```
17 Django Apps Total:

Core System:
├── accounts         - Custom user authentication
├── user_profile     - Extended user info
├── teams            - Team management (300+ teams)
└── tournaments      - Tournament system (THE PROBLEM)

Game Integration (TIGHTLY COUPLED):
├── game_valorant    - Valorant-specific logic
└── game_efootball   - eFootball-specific logic

Support Systems:
├── economy          - DeltaCoins currency
├── notifications    - Multi-channel notifications
├── dashboard        - User dashboard
└── ecommerce        - Store (in development)

Utilities:
├── common           - Shared utilities
├── corelib          - Core libraries
├── siteui           - UI components
└── [4 more apps]
```

---

## 🔴 The 4 Critical Problems

### Problem #1: Tight Coupling
```
tournaments app → game_valorant app (HARD DEPENDENCY)
tournaments app → game_efootball app (HARD DEPENDENCY)
tournaments app → teams app (HARD DEPENDENCY)
tournaments app → economy app (via signals!)
tournaments app → notifications app (via signals!)

Result: Cannot add new games without modifying tournament core
```

### Problem #2: "Signal Hell"
```
Create a Tournament:
    Tournament.save()
        ↓
    [INVISIBLE SIGNAL 1] Creates TournamentSettings
    [INVISIBLE SIGNAL 2] Creates ValorantConfig (if game=valorant)
    [INVISIBLE SIGNAL 3] Creates EfootballConfig (if game=efootball)

Register for Tournament:
    Registration.save()
        ↓
    [INVISIBLE SIGNAL 1] Creates PaymentVerification
    [INVISIBLE SIGNAL 2] Modifies Team.game field
    [INVISIBLE SIGNAL 3] Sends notification
    [INVISIBLE SIGNAL 4] Awards coins (if payment verified)

Result: Business logic is HIDDEN and UNPREDICTABLE
```

### Problem #3: Configuration Chaos
```
Tournament configuration spread across 8+ models:

1. Tournament (deprecated fields: slot_size, entry_fee_bdt, etc.)
2. TournamentSettings (20+ fields, overlaps with others)
3. TournamentSchedule (registration dates, duplicates Tournament fields)
4. TournamentCapacity (team slots, duplicates Tournament fields)
5. TournamentFinance (entry fee, duplicates Tournament fields)
6. TournamentMedia (banners, logos)
7. TournamentRules (rules text + behavior settings)
8. ValorantConfig (game-specific config)
9. EfootballConfig (game-specific config)

Result: NO SINGLE SOURCE OF TRUTH, data duplicated and inconsistent
```

### Problem #4: No Abstraction
```
Adding a new game requires changing:
- tournaments/signals.py (add new if/elif for game)
- tournaments/forms.py (add game-specific fields)
- tournaments/views.py (add game-specific validation)
- Create new game_xxx app with config model
- Update admin interface
- Update templates

6+ files to modify for EACH new game!

Result: CANNOT SCALE to 50+ games
```

---

## 📁 Key Files to Understand

### Models (Most Important)
```
apps/tournaments/models/
├── tournament.py         - Main Tournament model (300 lines)
├── registration.py       - Registration logic (100 lines)
├── match.py              - Match model (120 lines)
├── bracket.py            - Bracket structure (20 lines)
├── tournament_settings.py - Configuration (150 lines)
├── game_config.py        - Dynamic game config (NEW, 100 lines)
└── [15+ more model files]
```

### The Problem File
```
apps/tournaments/signals.py   - 300+ lines of hidden business logic
                                11+ signal handlers
                                Cross-app dependencies
                                Silent failures
                                THE MAIN PROBLEM!
```

### Game Integration
```
apps/game_valorant/models.py   - ValorantConfig (150 lines)
apps/game_efootball/models.py  - EfootballConfig (100 lines)

Problem: Each game needs its own app and model!
```

---

## 🔄 Key Workflows (Current)

### Tournament Creation Workflow
```
1. Admin creates Tournament in Django admin
2. SIGNAL auto-creates TournamentSettings
3. SIGNAL auto-creates game config (ValorantConfig if valorant)
4. Admin manually creates TournamentSchedule (separate page)
5. Admin manually creates TournamentCapacity (separate page)
6. Admin manually creates TournamentFinance (separate page)
7. Admin manually creates TournamentMedia (separate page)
8. Admin manually creates TournamentRules (separate page)

Result: 8 separate admin pages to fully configure a tournament!
```

### Registration Workflow
```
1. User/Team submits registration form
2. SIGNAL validates game requirements (hidden)
3. Registration saved to database
4. SIGNAL creates PaymentVerification record
5. SIGNAL updates Team.game field (side effect!)
6. SIGNAL sends notification
7. Admin manually verifies payment (separate admin page)
8. On verification, SIGNAL awards coins (hidden)

Result: Hidden side effects, manual steps, unclear flow
```

---

## 🎮 Game Integration (Current)

### Valorant
```python
# apps/game_valorant/models.py
class ValorantConfig(models.Model):
    tournament = OneToOneField(Tournament)
    best_of = CharField()          # BO1, BO3, BO5
    map_pool = ArrayField()        # Selected maps
    rounds_per_match = IntegerField()
    # ... 15+ more fields

Requirements:
- 5 players + 2 subs (HARDCODED)
- Riot ID validation (HARDCODED)
- Team-only (no solo) (HARDCODED)
```

### eFootball
```python
# apps/game_efootball/models.py
class EfootballConfig(models.Model):
    tournament = OneToOneField(Tournament)
    format_type = CharField()      # BO1, BO3, BO5
    match_duration_min = IntegerField()
    team_strength_cap = IntegerField()
    # ... 10+ more fields

Requirements:
- 1 player (solo) OR 2 players (team) (HARDCODED)
- Platform ID validation (HARDCODED)
```

### Problem
**To add CS2, PUBG, Dota 2, MLBB, Free Fire, FC26:**
- Must create 6 new apps
- Must modify tournaments/signals.py 6 times
- Must duplicate validation logic 6 times
- Must create 6 admin interfaces

**Impossible to scale!**

---

## 💾 Database Schema (Simplified)

```
tournaments_tournament (main table)
    ↓ OneToOne
tournaments_tournamentsettings
    ↓ OneToOne
tournaments_tournamentschedule
    ↓ OneToOne
tournaments_tournamentcapacity
    ↓ OneToOne
tournaments_tournamentfinance
    ↓ OneToOne
game_valorant_valorantconfig (if game=valorant)
    OR
game_efootball_efootballconfig (if game=efootball)

tournaments_tournament
    ↓ ForeignKey (many)
tournaments_registration
    ↓ ForeignKey
teams_team (team registration)
    OR
user_profile_userprofile (solo registration)

tournaments_registration
    ↓ OneToOne
tournaments_paymentverification
```

**Problem:** Too many tables, redundant data, unclear relationships

---

## 🧪 Testing Structure

```
tests/
├── test_part1_tournament_core.py       - Core tournament tests
├── test_part2_game_configs.py          - Game integration tests
├── test_part3_payments.py              - Payment verification tests
├── test_part4_teams.py                 - Team tests
├── test_part5_coin.py                  - Economy integration tests
├── test_partB_team_presets.py          - Team setup tests
├── test_partB2_valorant_preset_integration.py
├── test_partB2_efootball_preset_integration.py
└── [86+ more test files]

Problem: Tests must account for signals, making them complex
```

---

## 📋 What the New System Needs

### Must Have:
1. **Decouple games** - Plugin architecture, no hardcoding
2. **Eliminate signals** - Explicit service layer
3. **Unify configuration** - Single source of truth
4. **Abstract formats** - Support any tournament type
5. **Simplify admin** - Unified management interface

### Should Support:
- 50+ games easily
- Solo, team, and mixed tournaments
- Any tournament format (bracket, points, battle royale)
- Custom team sizes per tournament
- Multi-game tournaments
- Game variations (1v1, 3v3, 5v5)

---

## 🔍 How to Explore the Code

### Start Here:
1. `apps/tournaments/models/tournament.py` - Main model
2. `apps/tournaments/signals.py` - See the problems
3. `apps/game_valorant/models.py` - Game integration example
4. `apps/tournaments/views/registration_unified.py` - Registration flow

### To Understand Problems:
1. Create a tournament in local environment
2. Watch what gets created in database (8+ records!)
3. Try to add a new game (realize you must modify 6+ files)
4. Try to debug why Team.game changed (trace signals)

---

## 📚 Read These Documents in Order

1. **`00_README_START_HERE.md`** - Start here!
2. **`01_PROJECT_OVERVIEW.md`** - Understand the full project
3. **`02_CURRENT_TECH_STACK.md`** - Know the technologies
4. **`10_CURRENT_PROBLEMS.md`** - See all the problems
5. **`06_SIGNAL_SYSTEM_ANALYSIS.md`** - Understand signal hell

Then explore the codebase with context!

---

## 🎯 Your Mission

**Redesign the tournament system to be:**
- Modular (plugin-based games)
- Explicit (no signal magic)
- Flexible (any game, any format)
- Maintainable (clear code structure)
- Scalable (50+ games easily)

**Preserve:**
- Existing tournament data
- Core business logic
- User experience
- API compatibility (where reasonable)

**Good luck!** 🚀

---

**Last Updated:** November 2, 2025  
**Purpose:** Quick onboarding for new development team
