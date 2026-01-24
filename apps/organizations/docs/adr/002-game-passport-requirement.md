# ADR-002: Game Passport Requirement for Roles

**Status:** ✅ Accepted  
**Date:** 2026-01-25  
**Deciders:** Engineering Team  
**Related Docs:** [TEAM_ORG_ARCHITECTURE.md](../../../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_ARCHITECTURE.md) §6.2 Game Passport Integration

---

## Context

DeltaCrown platform requires players to have **Game Passports** (verified game accounts) to participate in tournaments. However, teams include various roles beyond players:

**Playing Roles:**
- **PLAYER** (Starter) - Active roster member who plays in matches
- **SUBSTITUTE** - Bench player available for substitution

**Non-Playing Roles:**
- **COACH** - Strategic advisor, no in-game participation
- **ANALYST** - Data/stats specialist, no in-game participation
- **MANAGER** - Administrative role (roster, registrations)
- **SCOUT** - Talent identification for organizations
- **OWNER** - Independent team owner (management only)

**Problem:** Should all roles require Game Passports, or only playing roles?

**Business Constraints:**
- Tournament registration requires valid Game Passports for all **playing members**
- Coaches/analysts may not have active game accounts
- Requiring passport for non-playing roles creates unnecessary friction
- However, substitutes MUST have passports (can be subbed in during match)

---

## Decision

**We will require Game Passports ONLY for PLAYER and SUBSTITUTE roles when assigned to STARTER or SUBSTITUTE roster slots.**

Implementation in `apps/organizations/models/membership.py`:

```python
class TeamMembership(models.Model):
    role = models.CharField(
        max_length=20,
        choices=MembershipRole.choices,
        help_text="Organizational role within team"
    )
    roster_slot = models.CharField(
        max_length=20,
        choices=RosterSlot.choices,
        null=True,
        blank=True,
        help_text="Physical roster slot (STARTER/SUBSTITUTE/COACH/ANALYST)"
    )
    
    def requires_game_passport(self) -> bool:
        """
        Check if this membership requires a Game Passport.
        
        Returns:
            True if role is PLAYER or SUBSTITUTE in playing slot
        """
        playing_roles = [MembershipRole.PLAYER, MembershipRole.SUBSTITUTE]
        playing_slots = [RosterSlot.STARTER, RosterSlot.SUBSTITUTE]
        
        return (
            self.role in playing_roles and 
            self.roster_slot in playing_slots
        )
```

**Validation Logic:**
```python
# In TeamService.validate_tournament_roster()
for member in active_members:
    if member.requires_game_passport():
        passport = GamePassportService.get_passport(member.user_id, team.game_id)
        if not passport or not passport.is_verified:
            errors.append(f"{member.user.username} missing valid Game Passport")
```

---

## Consequences

### Positive

✅ **Reduces Friction:** Coaches/analysts/managers don't need game accounts to join teams  
✅ **Business Logic Clarity:** Single method (`requires_game_passport()`) encapsulates rule  
✅ **Flexibility:** Organizations can hire coaches without active player accounts  
✅ **Tournament Compliance:** Still enforces passport requirement where it matters (actual players)

### Negative

❌ **Role-Slot Coupling:** Logic depends on BOTH role AND roster_slot fields being set correctly  
❌ **Validation Complexity:** Service layer must check passport requirement at multiple points:
  - Team member addition
  - Tournament registration
  - Roster slot changes (COACH → SUBSTITUTE requires passport)

### Neutral

🔶 **Edge Case: Role Changes:** If COACH promoted to SUBSTITUTE, must validate passport before allowing  
🔶 **Substitute Requirement:** Substitutes require passport even if rarely play (acceptable trade-off for flexibility)

---

## Alternatives Considered

### Alternative 1: All Roles Require Game Passport ❌

**Approach:** Every team member must have verified Game Passport regardless of role.

**Pros:**
- Simplest validation logic (no conditionals)
- Everyone "ready to play" if needed
- Easier tournament eligibility checks

**Cons:**
- **Unrealistic for coaches:** Many successful coaches are retired players without active accounts
- **Organizational friction:** Scouts, analysts don't need game accounts for their job
- **Competitive disadvantage:** Teams forced to hire only candidates with game experience

**Rejection Reason:** Creates unnecessary barrier to entry for non-playing staff roles.

---

### Alternative 2: No Game Passport Requirement ❌

**Approach:** Passports optional, validate only at tournament check-in time.

**Pros:**
- Maximum flexibility for team formation
- No upfront validation needed

**Cons:**
- **Late failure risk:** Team registers for tournament, then fails check-in because player lacks passport
- **Poor UX:** Error discovered hours/days after registration deadline
- **Tournament disruption:** Last-minute scrambles to find replacement players

**Rejection Reason:** Defers validation too late, creates tournament operations headaches.

---

### Alternative 3: Passport Required Only for PLAYER Role (Not SUBSTITUTE) ❌

**Approach:** Only starters need passport, substitutes exempt.

**Pros:**
- Slightly less friction for bench players
- Easier to fill substitute slots

**Cons:**
- **Tournament compliance risk:** Substitutes CAN play in matches if subbed in
- **Inconsistent logic:** Why would substitute not need what player needs?
- **Edge case complexity:** What if starter injured and sub must play?

**Rejection Reason:** Substitutes are still playing roles and must be tournament-ready.

---

### Alternative 4: Separate PassportRequired Boolean Field ❌

**Approach:** Add `passport_required` boolean field to TeamMembership.

**Pros:**
- Explicit per-member control
- Can override rule for special cases

**Cons:**
- **Redundant data:** Passport requirement fully derivable from role + slot
- **Consistency risk:** Developer could set inconsistent values
- **Maintenance burden:** Two sources of truth for same rule

**Rejection Reason:** YAGNI (You Aren't Gonna Need It) - role-based logic sufficient.

---

## Implementation Notes

### Validation Points

**1. Team Member Addition (apps/organizations/services/team_service.py - Phase 2):**
```python
def add_team_member(team_id: int, user_id: int, role: str, roster_slot: str) -> TeamMembership:
    membership = TeamMembership(team_id=team_id, user_id=user_id, role=role, roster_slot=roster_slot)
    
    if membership.requires_game_passport():
        passport = GamePassportService.get_passport(user_id, team.game_id)
        if not passport or not passport.is_verified:
            raise ValidationError("User must have verified Game Passport for this role")
    
    membership.save()
    return membership
```

**2. Tournament Registration (apps/tournaments/services/registration_service.py - Phase 3):**
```python
def validate_roster(team_id: int, tournament_id: int) -> ValidationResult:
    team = TeamService.get_team_by_id(team_id)
    active_members = TeamMembership.objects.filter(team=team, status=MembershipStatus.ACTIVE)
    
    errors = []
    for member in active_members:
        if member.requires_game_passport():
            passport = GamePassportService.get_passport(member.user_id, team.game_id)
            if not passport or not passport.is_verified:
                errors.append(f"{member.user.username} missing valid Game Passport")
    
    return ValidationResult(is_valid=len(errors) == 0, errors=errors)
```

**3. Roster Slot Changes:**
```python
# If changing COACH → SUBSTITUTE, validate passport first
old_slot = membership.roster_slot
membership.roster_slot = new_slot

if not old_membership.requires_game_passport() and membership.requires_game_passport():
    # Validate passport before allowing change
    passport = GamePassportService.get_passport(membership.user_id, team.game_id)
    if not passport or not passport.is_verified:
        raise ValidationError("User must have verified Game Passport for SUBSTITUTE slot")
```

### Testing

Test coverage in `apps/organizations/tests/test_membership.py`:
- `test_requires_game_passport_player_starter()` - Returns True
- `test_requires_game_passport_substitute_sub_slot()` - Returns True
- `test_requires_game_passport_coach_does_not()` - Returns False
- `test_requires_game_passport_analyst_does_not()` - Returns False
- `test_requires_game_passport_manager_does_not()` - Returns False

---

## Future Considerations

### Phase 5+ Game Passport Integration

When Game Passport system fully integrated:
- Add FK: `game_passport = models.ForeignKey(GamePassport, null=True)`
- Validate on membership creation if `requires_game_passport()` returns True
- Cache passport status to avoid repeated API calls

### Multi-Game Teams (Future)

If team competes in multiple games:
- May need passport per game (e.g., LoL and Valorant passports)
- `requires_game_passport()` would check team.game_id
- User could have passports for multiple games

---

## References

**Planning Documents:**
- [TEAM_ORG_ARCHITECTURE.md](../../../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_ARCHITECTURE.md) - Section 6.2 Game Passport Integration
- [TEAM_ORG_ENGINEERING_STANDARDS.md](../../../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_ENGINEERING_STANDARDS.md) - Section 5.4 Validation Standards

**Related Code:**
- `apps/organizations/models/membership.py` - TeamMembership model
- `apps/organizations/choices.py` - MembershipRole and RosterSlot enums
- `apps/organizations/tests/test_membership.py` - Game passport requirement tests

**Business Rules:**
- Tournament registration requirements (games/docs/tournament_rules.md)
- Game Passport verification flow (games/docs/passport_verification.md)

---

**Last Updated:** 2026-01-25  
**Status:** Active - Method implemented, service layer validation in Phase 2
