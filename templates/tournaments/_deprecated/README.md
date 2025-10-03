# Deprecated Registration Templates

⚠️ **WARNING: These templates are deprecated and no longer used.**

## Migration Complete

All registration flows now use the **modern registration system**:
- **Primary Template**: `templates/tournaments/modern_register.html`
- **Primary View**: `apps/tournaments/views/registration_modern.py`

## What Happened

These templates were part of the old registration system that has been replaced with a unified, professional implementation:

### Deprecated Templates (Moved Here):
- `register.html` - Original registration template
- `unified_register.html` - Unified registration system
- `valorant_register.html` - Game-specific Valorant registration
- `efootball_register.html` - Game-specific eFootball registration
- `enhanced_solo_register.html` - Enhanced solo registration
- `enhanced_team_register.html` - Enhanced team registration

### Why They Were Deprecated:
1. **Code Duplication**: Multiple templates with 80% similar code
2. **Inconsistent Logic**: Different validation/state handling across templates
3. **Hard to Maintain**: Changes needed in 5+ files instead of 1
4. **No State Machine**: Used scattered date/status checks
5. **Poor UX**: Static pages without real-time updates

## Modern System Benefits

✅ **Single Source of Truth**: One template handles all registration types  
✅ **State Machine**: Uses `TournamentStateMachine` for consistent logic  
✅ **Auto-fill**: Pre-fills data from user profile and team  
✅ **Multi-step**: Progressive form with validation  
✅ **Real-time Updates**: Live state changes without refresh  
✅ **API-driven**: REST endpoints for validation/submission  
✅ **Approval Workflow**: Built-in request approval system  
✅ **Game-agnostic**: Works for any game type  

## Migration Timeline

- **2025-10-03**: Templates moved to `_deprecated/`
- **2025-10-03**: URLs redirect to modern system with warning message
- **Version 2.0**: These files will be permanently deleted

## Safe to Delete?

**Yes**, these templates are no longer referenced anywhere in the codebase:
- All URLs redirect to `modern_register_view`
- All JavaScript uses `/tournaments/register-modern/<slug>/`
- All internal links updated to `tournaments:modern_register`

## Rollback Plan (Emergency Only)

If you need to temporarily revert:

1. Copy template back to `templates/tournaments/`
2. Update `apps/tournaments/urls.py` to import from original views
3. Remove deprecation wrapper from `_deprecated.py`

**Note**: Not recommended - modern system is far superior and well-tested.

## Questions?

See documentation:
- `docs/TOURNAMENT_STATE_MACHINE_REFACTORING.md` - Phase 1 (State Machine)
- `docs/TOURNAMENT_CODE_CONSOLIDATION.md` - Phase 2 (This cleanup)

---

**Last Updated**: October 3, 2025  
**Deprecated By**: Tournament System Refactoring Phase 2
