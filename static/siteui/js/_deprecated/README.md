# Deprecated JavaScript Files

⚠️ **WARNING: These files are no longer used in active code.**

## Moved Here: October 3, 2025

### Phase 3: JavaScript/CSS Cleanup

These JavaScript files were part of the old tournament system and have been replaced by modern, generic implementations.

## Files in This Directory

### 1. `valorant-tournament.js` (16KB)
- **Purpose**: Game-specific registration form for Valorant
- **Used By**: `templates/tournaments/_deprecated/valorant_register.html`
- **Replaced By**: `modern_register.html` (game-agnostic)
- **Why Deprecated**: 
  - Game-specific, not reusable
  - Hardcoded Valorant logic
  - Replaced by modern registration system

### 2. `tournament-register-neo.js` (6KB)
- **Purpose**: Old registration form interactions
- **Used By**: `templates/tournaments/_deprecated/register.html`
- **Replaced By**: `registration_modern.py` + state machine
- **Why Deprecated**:
  - Part of old registration flow
  - No state machine integration
  - Replaced by modern registration

## Modern Replacements

### Old System:
```javascript
// Game-specific files (valorant-tournament.js, etc.)
// Custom logic for each game
// No state machine
// Static validation
```

### New System:
```javascript
// tournament-detail-modern.js - Generic registration buttons
// tournament-state-poller.js - Real-time state updates
// tournament-card-dynamic.js - Dynamic card rendering
// Uses TournamentStateMachine for all logic
```

## Migration Complete

✅ All active templates updated to use modern JS  
✅ Registration now uses `registration_modern.py`  
✅ State machine handles all validation  
✅ Generic, reusable components  

## Safe to Delete?

**Not yet** - Kept for reference during transition period.

**Deletion Timeline**:
- **Oct 2025**: Moved to `_deprecated/`
- **Nov 2025**: Monitor for any missed references
- **Jan 2026**: Safe to delete permanently

## Rollback (Emergency Only)

If needed:
```bash
cd static/siteui/js
mv _deprecated/valorant-tournament.js ./
mv _deprecated/tournament-register-neo.js ./
```

**Not recommended** - Modern system is far superior.

---

**Last Updated**: October 3, 2025  
**Part of**: Tournament System Refactoring Phase 3
