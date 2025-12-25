# UP-GAME-PROFILE-ARCHITECTURE
## First-Class Game Profile System Design

**Status:** Architecture Review  
**Date:** 2024-12-24  
**Author:** AI Agent (supervised by RK Rashik)  
**Phase:** Data Model + Integration Design

---

## Executive Summary

Design a **normalized, extensible game profile system** that:
- Supports 11 games (VALORANT, CS2, Dota 2, MLBB, PUBGM, etc.)
- Eliminates JSON schema churn
- Provides admin-friendly UX
- Integrates with tournaments/stats/privacy
- Scales to 20+ games without migrations

**Key Decision:** Use **separate GameProfile model** with foreign key to UserProfile.

---

## 1. Current State Analysis

### 1.1 What Exists

**UserProfile Model:**
```python
game_profiles = models.JSONField(default=list, blank=True)
# Structure: [{"game": "valorant", "ign": "Player#TAG", "rank": "Immortal", ...}]
```

**GameProfile Model (ALREADY EXISTS):**
```python
class GameProfile(models.Model):
    user = models.ForeignKey(User, on_delete=CASCADE, related_name='game_profiles')
    game = models.CharField(max_length=20, choices=GAME_CHOICES)
    in_game_name = models.CharField(max_length=100)
    rank_name = models.CharField(max_length=50, blank=True)
    main_role = models.CharField(max_length=50, blank=True)
    matches_played = models.IntegerField(default=0)
    win_rate = models.IntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['user', 'game']]
```

**Problem:** Dual system exists!
- JSONField `game_profiles` (legacy, used by FE/admin)
- Separate `GameProfile` model (normalized, underutilized)

### 1.2 Integration Points

**Tournament Registration:**
- `apps/tournaments/views/registration_wizard.py` (lines 465-478)
- Hardcoded: `if game_slug == 'valorant': auto_filled['game_id'] = profile.riot_id`
- **Legacy fields removed in migration 0011** (riot_id, steam_id, etc.)

**Admin:**
- `UserProfileAdmin` uses `GameProfilesField` (JSON text editor)
- `GameProfileInline` exists but not prominent

**Frontend:**
- Templates access `profile.game_profiles` (JSON)
- Context builder passes JSON to FE

---

## 2. Architecture Decision

### 2.1 Primary Model: GameProfile (Normalized)

**Decision:** **Deprecate JSONField, promote GameProfile model as primary.**

**Rationale:**
1. **Already exists** — no new model needed
2. **Django admin-native** — TabularInline, filters, search work out of box
3. **Query-friendly** — `GameProfile.objects.filter(game='valorant', rank_tier__gte=7)`
4. **Audit-ready** — AuditService logs changes per row
5. **Extensible** — Add columns without JSON schema migrations

### 2.2 Schema Design

**Current GameProfile Model (Keep + Enhance):**

```python
class GameProfile(models.Model):
    # Core Identity
    user = models.ForeignKey(User, on_delete=CASCADE, related_name='game_profiles')
    game = models.CharField(max_length=20, choices=GAME_CHOICES)
    
    # Game Identity (per-game format)
    in_game_name = models.CharField(max_length=100)
    
    # Competitive Data
    rank_name = models.CharField(max_length=50, blank=True)
    rank_tier = models.IntegerField(default=0)  # Numeric for sorting
    peak_rank = models.CharField(max_length=50, blank=True)
    
    # Role/Position
    main_role = models.CharField(max_length=50, blank=True)
    
    # Stats
    matches_played = models.IntegerField(default=0)
    win_rate = models.IntegerField(default=0)  # 0-100
    kd_ratio = models.FloatField(null=True, blank=True)
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_method = models.CharField(max_length=50, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # NEW: Per-game flexible data
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Game-specific fields (e.g., MLBB server_id, PUBGM tier_level)"
    )
    
    class Meta:
        unique_together = [['user', 'game']]
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'game']),
            models.Index(fields=['game', '-rank_tier']),
            models.Index(fields=['-updated_at']),
        ]
```

**Additions Needed:**
1. `verified_at` — timestamp of verification
2. `verification_method` — "riot_api", "manual_admin", "screenshot"
3. `metadata` — JSONB for game-specific overflow (MLBB server_id, region codes)

### 2.3 Game-Specific Extensions

**Use `metadata` JSONField for per-game nuances:**

**VALORANT:**
```json
{
  "tagline": "1234",
  "region": "NA",
  "peak_episode": "E7A3"
}
```

**MLBB:**
```json
{
  "server_id": "1234",
  "emblem_config": "Fighter-Tank"
}
```

**PUBGM:**
```json
{
  "character_id": "5123456789",
  "tier_level": 50
}
```

**Benefit:** Add new fields without schema migrations.

---

## 3. Migration Plan

### 3.1 Current State

**JSONField Exists:** `UserProfile.game_profiles = [...]`  
**Normalized Model Exists:** `GameProfile` table with rows

**Strategy:** **Dual-write during transition, then cutover.**

### 3.2 Migration Phases

**Phase 1: Data Backfill (Zero Downtime)**
```sql
-- Ensure all JSON entries have GameProfile rows
INSERT INTO user_profile_gameprofile (user_id, game, in_game_name, ...)
SELECT 
    up.user_id,
    gp->>'game',
    gp->>'ign',
    ...
FROM user_profile_userprofile up,
     jsonb_array_elements(up.game_profiles) AS gp
WHERE NOT EXISTS (
    SELECT 1 FROM user_profile_gameprofile 
    WHERE user_id = up.user_id AND game = gp->>'game'
);
```

**Phase 2: Code Cutover**
- Update services to read/write GameProfile model
- Keep JSONField as read-only cache (for backward compat)
- Run backfill script weekly until cutover

**Phase 3: JSONField Deprecation**
- Mark `game_profiles` JSONField as deprecated
- Remove writes to JSONField
- Drop column in future migration (6 months buffer)

### 3.3 Zero Data Loss Strategy

**Validation Script:**
```python
def validate_game_profile_parity():
    """Ensure JSON and GameProfile rows match."""
    for profile in UserProfile.objects.all():
        json_games = {gp['game'] for gp in profile.game_profiles}
        model_games = set(profile.user.game_profiles.values_list('game', flat=True))
        
        if json_games != model_games:
            logger.error(f"Mismatch for user {profile.user.username}")
            # Trigger reconciliation
```

**Run before cutover:** Ensure 100% parity.

---

## 4. Integration Architecture

### 4.1 UserProfile Integration

**Relationship:**
```python
# User → GameProfiles (1:N)
user.game_profiles.all()  # QuerySet[GameProfile]

# UserProfile helper methods (keep for backward compat)
profile.get_game_id('valorant')  # Returns IGN
profile.has_game_profile('valorant')  # Boolean
```

**Deprecate JSONField methods:**
- `profile.get_game_profile(game)` → Use `GameProfile.objects.get(user=user, game=game)`
- `profile.set_game_profile(game, data)` → Use `GameProfileService.save_game_profile()`

### 4.2 Tournament Integration

**Current (Broken):**
```python
if game_slug == 'valorant':
    auto_filled['game_id'] = profile.riot_id  # Field removed!
```

**New (Service-Based):**
```python
from apps.user_profile.services import GameProfileService

game_profile = GameProfileService.get_game_profile(user, game_slug)
if game_profile:
    auto_filled['game_id'] = game_profile.in_game_name
```

**Service Contract:**
```python
class GameProfileService:
    @staticmethod
    def get_game_profile(user: User, game_slug: str) -> Optional[GameProfile]:
        """Get game profile for user (with caching)."""
        
    @staticmethod
    def get_game_id(user: User, game_slug: str) -> str:
        """Get IGN/game ID only (shorthand)."""
```

### 4.3 Stats Derivation

**Tournament Results → GameProfile Stats:**

```python
# After match completion
from apps.user_profile.services import StatsService

StatsService.update_game_profile_stats(
    user=player,
    game='valorant',
    result={
        'match_id': 12345,
        'won': True,
        'kd_ratio': 1.8,
        'rank_change': +15
    }
)
```

**Stats Service:**
```python
class StatsService:
    @staticmethod
    def update_game_profile_stats(user, game, result):
        """Increment matches_played, recalc win_rate, update rank if changed."""
        profile, _ = GameProfile.objects.get_or_create(user=user, game=game)
        
        profile.matches_played += 1
        if result['won']:
            wins = int(profile.matches_played * profile.win_rate / 100) + 1
            profile.win_rate = int(wins / profile.matches_played * 100)
        
        # Update rank if provided
        if 'rank_name' in result:
            old_rank = profile.rank_name
            profile.rank_name = result['rank_name']
            
            # Audit log rank change
            AuditService.record_event(...)
        
        profile.save()
```

### 4.4 Privacy Integration

**ProfileVisibilityPolicy:**
```python
def filter_game_profiles(game_profiles: List[GameProfile], viewer_role: str) -> List[Dict]:
    """Filter game profiles based on privacy settings."""
    
    if viewer_role == 'owner':
        return [serialize_full(gp) for gp in game_profiles]
    
    elif viewer_role == 'public':
        # Respect profile.show_game_profiles setting
        if not profile.show_game_profiles:
            return []
        
        # Show only: game, in_game_name, rank_name (no stats, no verification)
        return [serialize_public(gp) for gp in game_profiles]
```

**Add to UserProfile:**
```python
show_game_profiles = models.BooleanField(
    default=True,
    help_text="Display game profiles on public profile"
)
```

---

## 5. Service Layer

### 5.1 GameProfileService (Enhanced)

**Current State:** `apps/user_profile/services/game_profile_service.py` exists.

**Required Enhancements:**

```python
class GameProfileService:
    """Game profile CRUD with validation, audit, privacy."""
    
    @staticmethod
    @transaction.atomic
    def save_game_profile(
        user: User,
        game: str,
        in_game_name: str,
        rank_name: str = '',
        main_role: str = '',
        metadata: Dict = None,
        actor_user_id: int = None
    ) -> GameProfile:
        """Create or update game profile with audit logging."""
        
        # Validate game exists in SUPPORTED_GAMES
        if game not in SUPPORTED_GAMES:
            raise ValidationError(f"Unsupported game: {game}")
        
        # Validate IGN format per game
        validator = GameValidators.get_validator(game)
        if not validator.is_valid_ign(in_game_name):
            raise ValidationError(f"Invalid IGN format for {game}")
        
        # Get or create
        profile, created = GameProfile.objects.get_or_create(
            user=user,
            game=game,
            defaults={'in_game_name': in_game_name}
        )
        
        # Capture before state
        before = model_to_dict(profile) if not created else {}
        
        # Update fields
        profile.in_game_name = in_game_name
        profile.rank_name = rank_name
        profile.main_role = main_role
        if metadata:
            profile.metadata.update(metadata)
        profile.save()
        
        # Audit log
        AuditService.record_event(
            subject_user_id=user.id,
            actor_user_id=actor_user_id or user.id,
            event_type='game_profile.updated' if not created else 'game_profile.created',
            object_type='GameProfile',
            object_id=profile.id,
            before_snapshot=before,
            after_snapshot=model_to_dict(profile),
            metadata={'game': game}
        )
        
        return profile
    
    @staticmethod
    def get_game_profile(user: User, game: str) -> Optional[GameProfile]:
        """Get single game profile (with caching)."""
        try:
            return GameProfile.objects.get(user=user, game=game)
        except GameProfile.DoesNotExist:
            return None
    
    @staticmethod
    def get_all_game_profiles(user: User) -> List[GameProfile]:
        """Get all game profiles for user."""
        return list(GameProfile.objects.filter(user=user).order_by('-updated_at'))
    
    @staticmethod
    @transaction.atomic
    def delete_game_profile(user: User, game: str, actor_user_id: int = None) -> bool:
        """Delete game profile with audit."""
        try:
            profile = GameProfile.objects.get(user=user, game=game)
            before = model_to_dict(profile)
            profile_id = profile.id
            profile.delete()
            
            AuditService.record_event(
                subject_user_id=user.id,
                actor_user_id=actor_user_id or user.id,
                event_type='game_profile.deleted',
                object_type='GameProfile',
                object_id=profile_id,
                before_snapshot=before,
                after_snapshot={},
                metadata={'game': game}
            )
            return True
        except GameProfile.DoesNotExist:
            return False
```

### 5.2 Game Validators

**New Module:** `apps/user_profile/validators/game_validators.py`

```python
class GameValidators:
    """Per-game IGN validation rules."""
    
    @staticmethod
    def get_validator(game_slug: str):
        validators = {
            'valorant': ValorantValidator,
            'cs2': SteamValidator,
            'mlbb': MLBBValidator,
            # ... etc
        }
        return validators.get(game_slug, DefaultValidator)()

class ValorantValidator:
    def is_valid_ign(self, ign: str) -> bool:
        """Riot ID must match: Name#TAG (3-16 chars, #, 3-5 digits)"""
        import re
        return bool(re.match(r'^[a-zA-Z0-9\s]{3,16}#[a-zA-Z0-9]{3,5}$', ign))

class SteamValidator:
    def is_valid_ign(self, ign: str) -> bool:
        """Steam ID64: 17 digits starting with 7656"""
        return ign.isdigit() and len(ign) == 17 and ign.startswith('7656')

class MLBBValidator:
    def is_valid_ign(self, ign: str) -> bool:
        """MLBB Game ID: 9-10 digits"""
        return ign.isdigit() and 9 <= len(ign) <= 10
```

---

## 6. Schema Changes Required

### 6.1 GameProfile Model Migrations

**Migration:** `apps/user_profile/migrations/0012_enhance_game_profile.py`

```python
operations = [
    migrations.AddField(
        model_name='gameprofile',
        name='verified_at',
        field=models.DateTimeField(null=True, blank=True),
    ),
    migrations.AddField(
        model_name='gameprofile',
        name='verification_method',
        field=models.CharField(max_length=50, blank=True, default=''),
    ),
    migrations.AddField(
        model_name='gameprofile',
        name='metadata',
        field=models.JSONField(default=dict, blank=True),
    ),
    migrations.AddIndex(
        model_name='gameprofile',
        index=models.Index(fields=['-updated_at'], name='gp_updated_idx'),
    ),
]
```

### 6.2 UserProfile Privacy Field

**Migration:** `apps/user_profile/migrations/0013_add_game_profile_privacy.py`

```python
operations = [
    migrations.AddField(
        model_name='userprofile',
        name='show_game_profiles',
        field=models.BooleanField(
            default=True,
            help_text="Display game profiles on public profile"
        ),
    ),
]
```

---

## 7. Backward Compatibility

### 7.1 Transition Period

**Duration:** 3 months dual-write, then cutover.

**Dual-Write Logic:**
```python
def save_game_profile(user, game, data):
    # Write to GameProfile model (primary)
    profile = GameProfileService.save_game_profile(user, game, data['ign'], ...)
    
    # ALSO write to JSONField (for backward compat)
    user_profile = user.profile
    json_profiles = list(user_profile.game_profiles)
    
    # Update or append
    for i, gp in enumerate(json_profiles):
        if gp['game'] == game:
            json_profiles[i] = serialize_to_json(profile)
            break
    else:
        json_profiles.append(serialize_to_json(profile))
    
    user_profile.game_profiles = json_profiles
    user_profile.save(update_fields=['game_profiles'])
```

### 7.2 Helper Methods (Keep)

```python
# UserProfile model
def get_game_id(self, game_code):
    """Backward compat: Get IGN from GameProfile model."""
    try:
        gp = self.user.game_profiles.get(game=game_code)
        return gp.in_game_name
    except GameProfile.DoesNotExist:
        return ''

def has_game_profile(self, game_code):
    """Backward compat: Check if GameProfile exists."""
    return self.user.game_profiles.filter(game=game_code).exists()
```

---

## 8. Success Criteria

### 8.1 Pre-Cutover

- [ ] GameProfile backfill 100% complete (validate script passes)
- [ ] All tournament registration flows use `GameProfileService.get_game_id()`
- [ ] Admin UX shows GameProfileInline prominently
- [ ] FE templates read from `user.game_profiles.all()` (QuerySet)
- [ ] Privacy settings respect `show_game_profiles` flag

### 8.2 Post-Cutover

- [ ] JSONField marked deprecated (docstring warning)
- [ ] No code writes to `game_profiles` JSONField
- [ ] All tests green (100% pass rate)
- [ ] Performance: Game profile queries < 50ms (with indexes)

### 8.3 Future-Proof

- [ ] Add new game without migration (use `metadata` field)
- [ ] Admin can add/edit game profiles in 1 click
- [ ] Audit trail shows who changed game profiles + when

---

## 9. Rollback Plan

**If Issues Arise:**

1. **Revert to JSONField as primary** (feature flag: `USE_JSON_GAME_PROFILES = True`)
2. Keep GameProfile model for new entries only
3. Dual-read during recovery period
4. Re-attempt cutover after fixes

**Rollback Command:**
```bash
python manage.py set_feature_flag USE_JSON_GAME_PROFILES true
```

---

## 10. Next Steps

**After Architecture Approval:**

1. **UP-GAME-PROFILE-IMPL-01:** Enhance GameProfile model (add 3 fields)
2. **UP-GAME-PROFILE-IMPL-02:** Write backfill migration script
3. **UP-GAME-PROFILE-IMPL-03:** Update GameProfileService with validators
4. **UP-GAME-PROFILE-IMPL-04:** Update tournament integration (remove hardcoded logic)
5. **UP-GAME-PROFILE-IMPL-05:** Update FE templates to use QuerySet
6. **UP-GAME-PROFILE-IMPL-06:** Admin UX improvements (see admin design doc)

**Timeline:** 2 weeks for full implementation + testing.

---

## Appendix: Game Profile Data Model

**Current Games (11):**
- VALORANT (riot_id)
- CS2 (steam_id)
- Dota 2 (steam_id)
- EA FC 26 (ea_id)
- eFootball (efootball_id)
- PUBG Mobile (pubgm_id)
- MLBB (mlbb_id + server_id)
- Free Fire (freefire_id)
- COD Mobile (codm_uid)
- Rocket League (epic_id)
- Rainbow Six Siege (ubisoft_id)

**GameProfile Handles All:**
- `in_game_name` stores the primary ID
- `metadata` stores secondary fields (server_id, region, etc.)

---

**Document Status:** ✅ READY FOR REVIEW  
**Next Document:** UP_GAME_PROFILE_ADMIN_DESIGN.md
