# Seed Command Inventory

**Last Updated**: 2026-02-02  
**Status**: Canonical Reference  

---

## 📋 Required Seed Commands (Production)

These commands are **REQUIRED** for a functional DeltaCrown platform.

### 1. seed_games

**Location**: `apps/games/management/commands/seed_games.py`  
**Size**: 858 lines  
**Status**: ✅ **REQUIRED**

**Purpose**: Seeds 11 major esports games with comprehensive metadata

**What It Seeds**:
- `Game` - 11 games (LOL, VAL, CS2, DOTA2, RL, APEX, OW2, FORT, COD, R6, PUBG)
- `GameRosterConfig` - Min/max players, substitutes, role requirements
- `GameRole` - Competitive roles per game (Support, Carry, Tank, etc.)
- `GamePlayerIdentityConfig` - Identity field requirements (Riot ID, Steam ID, etc.)
- `GameTournamentConfig` - Match formats, scoring, verification rules

**Idempotency**: ✅ Yes (uses `update_or_create`)

**Usage**:
```bash
# Initial seed
python manage.py seed_games

# Re-seed (force update)
python manage.py seed_games --force
```

**Dependencies**: None (runs first)

---

### 2. seed_game_passport_schemas

**Location**: `apps/user_profile/management/commands/seed_game_passport_schemas.py`  
**Size**: 516 lines  
**Status**: ✅ **REQUIRED**

**Purpose**: Seeds per-game identity configuration (GamePassportSchema)

**What It Seeds**:
- `GamePassportSchema` - One record per game
- Identity field definitions (ign, discriminator, platform, region)
- Rank tier hierarchies (Bronze → Silver → Gold → etc.)
- Verification requirements per game
- Supported regions per game

**Idempotency**: ✅ Yes (schema-based updates)

**Usage**:
```bash
# Initial seed
python manage.py seed_game_passport_schemas

# Reset (delete and recreate)
python manage.py seed_game_passport_schemas --reset
```

**Dependencies**: Requires `seed_games` first (foreign key to Game)

**⚠️ Note**: This seeds CONFIGURATION (per-game rules), NOT user data.

---

### 3. seed_game_ranking_configs

**Location**: `apps/competition/management/commands/seed_game_ranking_configs.py`  
**Status**: ⚠️ **OPTIONAL** (only if COMPETITION_APP_ENABLED=1)

**Purpose**: Seeds competition ranking system configurations

**What It Seeds**:
- `GameRankingConfig` - Per-game ranking rules
- Ranking weights (win/loss/kill/death/assist)
- Tier thresholds (LP required for each rank)
- Decay policy (inactivity LP loss)
- Verification rules

**Idempotency**: ✅ Yes (uses `update_or_create`)

**Usage**:
```bash
python manage.py seed_game_ranking_configs
```

**Dependencies**: 
- Requires `seed_games` first
- Requires `COMPETITION_APP_ENABLED=1` in settings
- Requires competition app migrations applied

---

## 🔧 Optional Seed Commands (Development/Migration)

### 4. backfill_game_profiles

**Location**: `apps/user_profile/management/commands/backfill_game_profiles.py`  
**Size**: 245 lines  
**Status**: ⚠️ **OPTIONAL** (only for legacy user migration)

**Purpose**: Create GameProfile instances for existing users

**What It Seeds**:
- `GameProfile` - User game identities (one per user per game)
- Minimal skeleton (user fills details via UI later)

**Idempotency**: ✅ Yes (uses `get_or_create`)

**Usage**:
```bash
# Dry-run
python manage.py backfill_game_profiles --dry-run

# Specific user
python manage.py backfill_game_profiles --user alice

# All users (with safety limit)
python manage.py backfill_game_profiles --all --limit 100

# Specific game only
python manage.py backfill_game_profiles --all --game valorant
```

**Dependencies**:
- Requires `seed_games` first
- Requires `seed_game_passport_schemas` first
- Requires at least 1 user to exist (or exits gracefully)

**⚠️ When to use**:
- Migrating legacy users from old system
- NOT needed for fresh databases (GameProfiles created via UI/API)

---

## 🚫 DEPRECATED Commands (Do Not Use)

### ❌ seed_identity_configs_2026.py

**Location**: `apps/games/management/commands/seed_identity_configs_2026.py`  
**Status**: ❌ **DEPRECATED** (duplicate functionality)

**Why Deprecated**:
- `seed_games.py` already seeds `GamePlayerIdentityConfig` model
- Duplicate functionality creates confusion
- Referenced in old templates but not needed

**Evidence of Non-Usage**:
```bash
# seed_games.py already seeds GamePlayerIdentityConfig (line 17, 68, 810)
$ grep -n "GamePlayerIdentityConfig" apps/games/management/commands/seed_games.py
17:    GamePlayerIdentityConfig,
68:        self.stdout.write(f"  Total Identity Configs: {GamePlayerIdentityConfig.objects.count()}")
810:            identity, id_created = GamePlayerIdentityConfig.objects.update_or_create(
```

**References Found** (to be cleaned up):
- `scripts/seed_all.py:37` - Calls deprecated command
- `apps/user_profile/admin/game_passports.py:168` - Documentation string
- `apps/games/management/commands/cleanup_passport_schema.py` - References old command
- Templates reference old command name in error messages

**Action**: ❌ **DELETE** (after removing references)

---

### ❌ seed_identity_configs.py

**Location**: `apps/games/management/commands/seed_identity_configs.py`  
**Size**: 625 lines  
**Status**: ❌ **DEPRECATED** (duplicate functionality)

**Why Deprecated**:
- Same as `seed_identity_configs_2026.py` but older version
- Superseded by `seed_games.py` which is more comprehensive

**Action**: ❌ **DELETE** (after removing references)

---

### ❌ seed_core_data.py

**Location**: `apps/core/management/commands/seed_core_data.py`  
**Size**: 65 lines  
**Status**: ❌ **DEPRECATED** (superseded by seed_games.py)

**Why Deprecated**:
- Basic game seeder (only 65 lines)
- `seed_games.py` is canonical (858 lines, comprehensive)
- Incomplete compared to seed_games.py

**Action**: ❌ **DELETE** (keep seed_games.py as canonical)

---

### ❌ seed_default_games.py

**Location**: `apps/games/management/commands/seed_default_games.py`  
**Status**: ❌ **DEPRECATED** (superseded by seed_games.py)

**Action**: ❌ **DELETE**

---

## 📊 Seed Sequence (Production Bootstrap)

```bash
# REQUIRED SEQUENCE (order matters):
1. python manage.py migrate                      # Create all tables
2. python manage.py seed_games                   # Foundation (REQUIRED)
3. python manage.py seed_game_passport_schemas   # User identity config (REQUIRED)

# OPTIONAL (if using competition features):
4. python manage.py seed_game_ranking_configs    # Competition rankings

# OPTIONAL (if migrating legacy users):
5. python manage.py backfill_game_profiles --all # User game identities
```

---

## 🔍 Verification Commands

```bash
# Check what's seeded
python manage.py shell
>>> from apps.games.models import Game, GamePlayerIdentityConfig
>>> from apps.user_profile.models import GamePassportSchema
>>> Game.objects.count()  # Should be 11
>>> GamePlayerIdentityConfig.objects.count()  # Should be 40+
>>> GamePassportSchema.objects.count()  # Should be 11

# Check migrations applied
python manage.py showmigrations

# Check for errors
python manage.py check
```

---

## 📝 Command Comparison Matrix

| Command | Required | Seeds What | Lines | Idempotent | Dependencies |
|---------|----------|------------|-------|------------|--------------|
| seed_games | ✅ Yes | Game, Roster, Roles, Identity, Tournament | 858 | ✅ Yes | None |
| seed_game_passport_schemas | ✅ Yes | GamePassportSchema | 516 | ✅ Yes | seed_games |
| seed_game_ranking_configs | ⚠️ Optional | GameRankingConfig | - | ✅ Yes | seed_games, COMPETITION_APP_ENABLED=1 |
| backfill_game_profiles | ⚠️ Optional | GameProfile (user data) | 245 | ✅ Yes | seed_games, seed_game_passport_schemas, users |
| ~~seed_identity_configs_2026~~ | ❌ Deprecated | GamePlayerIdentityConfig | 1126 | ✅ Yes | Duplicate of seed_games |
| ~~seed_identity_configs~~ | ❌ Deprecated | GamePlayerIdentityConfig | 625 | ✅ Yes | Duplicate of seed_games |
| ~~seed_core_data~~ | ❌ Deprecated | Basic games | 65 | ✅ Yes | Superseded by seed_games |
| ~~seed_default_games~~ | ❌ Deprecated | Basic games | - | ✅ Yes | Superseded by seed_games |

---

## 🧹 Cleanup Actions Required

### Phase 1: Remove References

```bash
# Files with references to deprecated commands:
- scripts/seed_all.py (line 37)
- apps/user_profile/admin/game_passports.py (line 168)
- apps/games/management/commands/cleanup_passport_schema.py (lines 7, 106, 109)
- templates/user_profile/profile/settings/partials/_game_passports.html (line 1614)
- apps/user_profile/views/dynamic_content_api.py (lines 117, 187)
```

### Phase 2: Delete Deprecated Commands

```bash
# Delete these files:
rm apps/games/management/commands/seed_identity_configs_2026.py
rm apps/games/management/commands/seed_identity_configs.py
rm apps/core/management/commands/seed_core_data.py
rm apps/games/management/commands/seed_default_games.py
```

---

## ✅ Final Recommendation

**KEEP (Required)**:
- ✅ `seed_games.py` - Canonical game seeder
- ✅ `seed_game_passport_schemas.py` - User identity configuration
- ✅ `seed_game_ranking_configs.py` - Competition rankings (optional)
- ✅ `backfill_game_profiles.py` - User migration tool (optional)

**DELETE (Deprecated)**:
- ❌ `seed_identity_configs_2026.py` - Duplicate functionality
- ❌ `seed_identity_configs.py` - Duplicate functionality
- ❌ `seed_core_data.py` - Superseded by seed_games
- ❌ `seed_default_games.py` - Superseded by seed_games

**CANONICAL SEED PIPELINE**:
```bash
migrate → seed_games → seed_game_passport_schemas → (optional: seed_game_ranking_configs)
```
