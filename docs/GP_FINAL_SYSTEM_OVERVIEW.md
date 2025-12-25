# Game Passport System - Final Overview

**Status:** ✅ Production Ready  
**Version:** Phase 1 Complete  
**Date:** December 25, 2025  

---

## What is Game Passport?

The **Game Passport** system is DeltaCrown's unified player identity management framework. It replaces the legacy JSON-based game profile storage with a normalized, audited, and feature-rich model.

### Core Concept

Each user can have **multiple Game Passports** - one per game title (e.g., VALORANT, CS2, League of Legends). Each passport contains:

- **Identity Data**: In-game name, rank, role, stats
- **Privacy Controls**: PUBLIC, PROTECTED, PRIVATE visibility
- **Team Affiliation**: Current team badge (if applicable)
- **Activity Flags**: "Looking for Team" (LFT) status
- **Display Preferences**: Pinning (feature passports on profile)
- **Security**: Identity Lock cooldown system

### Key Features

1. **Battle Cards UI**: Featured Game Passports displayed as visually rich cards
2. **Identity Lock**: Prevents rapid name changes with cooldown
3. **Alias History**: Tracks all past in-game names for verification
4. **Team Badge Integration**: Shows current team affiliation automatically
5. **Audit Trail**: Complete change history for moderation/support

---

## How Tournaments & Teams Use Game Passport

### Tournament Registration

When players register for tournaments, the system:

1. **Validates Identity**: Checks passport exists for tournament game
2. **Verifies Team**: If team registration, confirms team game matches passport game
3. **Locks Identity**: Prevents changes during active tournament participation
4. **Captures Snapshot**: Records IGN at time of registration

**Example Flow:**
```python
# Tournament registration validates passport
passport = GamePassportService.get_passport(user=player, game='valorant')
if not passport:
    raise ValidationError("No VALORANT Game Passport found")

# Lock identity for tournament duration
GamePassportService.lock_identity(
    user=player,
    game='valorant',
    lock_until=tournament_end_date + timedelta(days=3),
    reason=f"Tournament: {tournament.name}"
)
```

### Team Roster Management

Teams interact with passports via:

- **Team Badge Display**: Passport automatically shows team affiliation when TeamMembership exists
- **Multi-Game Teams**: Players can have passports for multiple games, each showing different team
- **Free Agent Status**: Passports without team show "Free Agent" badge
- **LFT Flag**: Players can enable "Looking for Team" to advertise availability

**Team Badge Logic:**
```django
{% if passport.current_team %}
<div class="team-badge">
    <img src="{{ passport.current_team.logo.url }}">
    <span>{{ passport.current_team.name }} [{{ passport.current_team.tag }}]</span>
</div>
{% else %}
<div class="team-badge">
    🆓 Free Agent
</div>
{% endif %}
```

---

## Admin Controls

### GameProfile Admin

**Search Capabilities:**
- Username
- Email
- Public ID (user_profile.public_id)
- In-game name
- Identity key
- Game title

**Filters Available:**
- Game (valorant, cs2, lol, etc.)
- Visibility (PUBLIC/PROTECTED/PRIVATE)
- LFT Status (Looking for Team)
- Pinned Status
- Locked/Unlocked (Identity Lock active)
- Creation date

**Display Columns:**
- User
- Game
- In-game name
- Visibility badge
- LFT badge
- Pinned status
- Lock countdown
- Team badge
- Created date

**Actions:**
- Bulk visibility change
- Bulk LFT toggle
- Bulk pin/unpin
- Manual identity lock
- View alias history
- View audit trail

### Identity Lock Management

Admins can:

1. **View Lock Status**: See countdown timer in admin list
2. **Manual Lock**: Apply lock to prevent impersonation
3. **Emergency Unlock**: Override lock for critical issues
4. **Lock History**: View all lock events in audit trail

**Lock Display:**
```
✓ Unlocked  (normal state)
🔒 Locked (14 days remaining)  (active lock)
```

### Privacy & Moderation

**Visibility Levels:**
- **PUBLIC**: Visible to everyone, indexed by search
- **PROTECTED**: Visible to authenticated users only
- **PRIVATE**: Visible to user + admins only

**Moderation Tools:**
- Force visibility to PRIVATE (hide problematic content)
- Lock identity (prevent impersonation)
- Review alias history (verify legitimacy)
- Audit trail (investigate changes)

---

## What is Explicitly Deferred to Phase 2+

### Phase 2 (NOT IMPLEMENTED YET)

❌ **Rank Verification System**
- Automated rank screenshot upload
- AI-powered rank detection
- Manual verification queue
- Rank dispute resolution

❌ **Advanced Stats Integration**
- API connections to game publishers
- Automatic stats updates
- Match history import
- Performance analytics

❌ **Passport Badges & Achievements**
- Tournament history badges
- Skill milestones
- Community achievements
- MVP awards

❌ **Multi-Account Management**
- Link multiple accounts per game
- Smurf account disclosure
- Account switching
- Cross-account stats

### Phase 3 (NOT IMPLEMENTED YET)

❌ **Verification Workflows**
- Identity verification for high-rank claims
- Pro player verification
- Official team affiliation verification
- Influencer verification

❌ **Integration Enhancements**
- Riot Games API integration
- Steam API integration
- Discord Rich Presence
- Twitch profile links

### Phase 4 (NOT IMPLEMENTED YET)

❌ **Legacy JSON Removal**
- Complete removal of `UserProfile.game_profiles` JSON field
- Migration scripts for any remaining data
- Schema cleanup

❌ **Performance Optimization**
- Database indexing tuning
- Query optimization
- Caching layer
- CDN integration for profile images

---

## Data Model Summary

### Primary Models

**GameProfile** (Game Passport)
```python
user: ForeignKey(User)
game: CharField (game slug)
in_game_name: CharField (current IGN)
visibility: CharField (PUBLIC/PROTECTED/PRIVATE)
is_lft: BooleanField (Looking for Team)
is_pinned: BooleanField (Featured on profile)
pinned_order: IntegerField (Display order)
locked_until: DateTimeField (Identity lock expiry)
rank_name: CharField (e.g., "Diamond II")
rank_image: ImageField
main_role: CharField (e.g., "Duelist")
metadata: JSONField (stats, KD, win rate, etc.)
```

**GameProfileAlias** (Alias History)
```python
game_profile: ForeignKey(GameProfile)
old_name: CharField (previous IGN)
changed_at: DateTimeField
changed_by_user_id: IntegerField
reason: TextField (optional)
```

**GameProfileConfig** (Game-Specific Rules)
```python
game: CharField (game slug)
lock_cooldown_days: IntegerField (default 30)
max_aliases_kept: IntegerField (default 10)
validation_regex: CharField (IGN format rules)
```

### Relationships

- `UserProfile` → `GameProfile` (one-to-many)
- `GameProfile` → `GameProfileAlias` (one-to-many)
- `GameProfile` ← `TeamMembership` (via game field match)
- `GameProfile` → `AuditEvent` (all changes logged)

---

## API Endpoints

### Public Endpoints

**GET** `/@<username>/` - View user's Battle Cards (public passports)

### Authenticated Endpoints

**POST** `/api/passports/toggle-lft/`
```json
{"game": "valorant"}
→ {"success": true, "is_lft": true}
```

**POST** `/api/passports/set-visibility/`
```json
{"game": "valorant", "visibility": "PRIVATE"}
→ {"success": true, "visibility": "PRIVATE"}
```

**POST** `/api/passports/pin/`
```json
{"game": "valorant", "pin": true}
→ {"success": true, "is_pinned": true}
```

**POST** `/api/passports/reorder/`
```json
{"game_order": ["valorant", "cs2", "lol"]}
→ {"success": true, "game_order": [...]}
```

### Legacy Endpoints (Still Supported)

**POST** `/api/profile/save-game-profiles-safe/`  
**POST** `/api/profile/update-game-id-safe/`  
**GET** `/api/profile/game-ids/`

These endpoints use `GamePassportService` internally and DO NOT touch legacy JSON field.

---

## Service Layer

### GamePassportService

Central service for all passport operations. All mutations go through this service to ensure:

- ✅ Validation
- ✅ Identity Lock enforcement
- ✅ Alias History tracking
- ✅ Audit Trail logging
- ✅ No direct JSON writes

**Key Methods:**
```python
# CRUD
create_passport(user, game, in_game_name, metadata)
get_passport(user, game)
get_all_passports(user)
update_identity(user, game, new_name, actor_user_id)
delete_passport(user, game, actor_user_id)

# Features
toggle_lft(user, game, actor_user_id)
set_visibility(user, game, visibility, actor_user_id)
pin_passport(user, game, actor_user_id)
unpin_passport(user, game, actor_user_id)
reorder_pinned_passports(user, game_order, actor_user_id)

# Security
lock_identity(user, game, lock_until, reason, actor_user_id)
unlock_identity(user, game, actor_user_id)
is_identity_locked(user, game)

# History
get_alias_history(user, game)
```

---

## Testing Coverage

### Test Suites

1. **test_game_passport.py** (21 tests)
   - CRUD operations
   - Validation rules
   - Identity Lock enforcement
   - Alias History tracking
   - Audit Trail verification

2. **test_gp_no_json_writes.py** (8 tests)
   - Confirms NO writes to legacy JSON field
   - Verifies service-only mutations
   - Ensures data integrity

3. **test_legacy_views_game_passport_migrated.py** (13 tests)
   - Legacy endpoint compatibility
   - Migration to service layer
   - Backward compatibility

4. **test_gp_fe_mvp_01.py** (9 tests)
   - URL routing
   - Template rendering
   - API endpoints
   - Service mutations

5. **test_gp_final_polish.py** (4 tests)
   - Team badge integration
   - Free Agent state
   - Terminology consistency

**Total:** 55 tests covering Game Passport system

---

## Performance Considerations

### Optimizations Implemented

✅ **Query Optimization**
- `select_related('user', 'user__profile')` on passport queries
- `prefetch_related('aliases')` for alias history
- Indexed fields: `user`, `game`, `in_game_name`, `locked_until`

✅ **Template Efficiency**
- Passport data attached to objects in view (avoid N+1)
- Team membership queried once per game
- Lazy loading for unpinned passports (collapsed by default)

✅ **Caching Strategy**
- Lock status cached on passport object
- Team badge data cached per request
- Admin list view uses `only()` for columns

### Known Limitations

⚠️ **No Global Caching** - Each page load queries database  
⚠️ **No CDN** - Profile images served directly from media storage  
⚠️ **No API Rate Limiting** - Mutation endpoints unthrottled  

These are addressed in Phase 4.

---

## Migration Path

### Current State (Phase 1 Complete)

✅ All passport data in normalized `GameProfile` table  
✅ Legacy JSON field preserved but unused  
✅ All endpoints migrated to service layer  
✅ UI fully updated to Battle Cards system  

### Phase 4 Cleanup (Future)

1. Run data verification script
2. Confirm zero JSON writes in production
3. Add migration to drop `game_profiles` column
4. Remove legacy endpoint compatibility layer
5. Update documentation

---

## Conclusion

The Game Passport system is **production-ready** with:

- ✅ Complete functionality for Phase 1 scope
- ✅ Zero legacy JSON writes
- ✅ Comprehensive test coverage (55 tests)
- ✅ Full audit trail
- ✅ Identity Lock protection
- ✅ Team Badge integration
- ✅ Consistent terminology

**NOT in scope for Phase 1:**
- ❌ Rank verification workflows
- ❌ Stats API integrations
- ❌ Achievement system
- ❌ Multi-account management

**Phase 1 Status:** 🎉 **100% COMPLETE** - Ready for production deployment

For questions or issues, contact the development team or file a ticket in the ops repository.

---

**Document Version:** 1.0  
**Last Updated:** December 25, 2025  
**Maintained By:** DeltaCrown Engineering Team
