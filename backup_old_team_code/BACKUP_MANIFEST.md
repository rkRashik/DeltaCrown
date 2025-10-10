# Backup Manifest - Legacy Code Archive

**Date Created:** October 9, 2025  
**Purpose:** Archive legacy code, experiments, and unused assets before Task 10 cleanup

---

## 📋 Contents

### 1. Legacy Models
**Status:** Retained but documented as legacy
- `apps/teams/models/_legacy.py` - Core legacy models (Team, TeamMembership, TeamInvite)
  - Contains TEAM_MAX_ROSTER constant
  - Legacy field structures maintained for backward compatibility
  - Referenced by migrations 0003, 0004, 0011, 0017

### 2. TODO Items Identified
**Location:** `apps/teams/services/sponsorship.py`
- Line 63: TODO: Send notification email to sponsor contact
- Line 64: TODO: Send notification to team admins
- Line 202: TODO: Implement email notification
- Line 210: TODO: Implement email notification
- Line 341: TODO: Send confirmation email

**Status:** These TODOs are now completed via Task 9 notification system
**Action:** Replace TODOs with actual notification service calls

**Location:** `apps/teams/views/sponsorship.py`
- Line 119: TODO: Send notification email to team admins

**Status:** Completed via Task 9
**Action:** Update with notification service call

### 3. Legacy References to Update
- `apps/teams/models/__init__.py`: 
  - Line 12: `from ._legacy import TEAM_MAX_ROSTER`
  - Line 18: `from .stats import TeamStats as LegacyTeamStats`
  - Line 75-78: Legacy models section

### 4. Migration References
- `0003_alter_team_logo.py` - Uses `apps.teams.models._legacy.team_logo_path`
- `0004_team_game.py` - References legacy teams in help text
- `0011_alter_team_game.py` - References legacy teams in help text
- `0017_team_description_team_logo...` - Uses `_legacy.team_logo_path`

---

## ✅ Actions Completed

### Phase 1: Documentation
- [x] Created backup directory structure
- [x] Generated manifest of legacy code
- [x] Identified TODO items

### Phase 2: TODO Resolution (Task 10)
- [ ] Replace sponsorship TODOs with NotificationService calls
- [ ] Update legacy imports to modern equivalents
- [ ] Add deprecation warnings where appropriate

### Phase 3: Migration Cleanup (Task 10)
- [ ] Review old migrations for consolidation
- [ ] Document which migrations must be retained
- [ ] Archive squashed migrations if applicable

---

## 🚫 DO NOT DELETE

The following files must remain for backward compatibility:
1. `_legacy.py` - Core models still in active use
2. Migrations 0001-0017 - Required for database schema
3. `LegacyTeamStats` - Kept for API compatibility

---

## 📝 Notes

**Legacy Code Strategy:**
- `_legacy.py` is not truly "legacy" - it's the active implementation
- Name is historical; code is production-ready
- Modern modules import from `_legacy.py` for stability
- No actual deprecated code found requiring backup

**Conclusion:**
- No code needs to be moved to backup at this time
- All "legacy" references are to maintained, production code
- Focus cleanup efforts on TODO resolution and optimization

---

**Last Updated:** October 9, 2025  
**Reviewed By:** Task 10 Implementation  
**Status:** Documentation Complete
