# ADR-001: Team Ownership Constraint (Organization XOR Owner)

**Status:** ✅ Accepted  
**Date:** 2026-01-25  
**Deciders:** Engineering Team  
**Related Docs:** [TEAM_ORG_ARCHITECTURE.md](../../../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_ARCHITECTURE.md) §2.1 Database Strategy

---

## Context

The Team & Organization vNext system must support two distinct team ownership models:

1. **Organization-Owned Teams:** Professional esports teams managed by verified organizations (e.g., Team Liquid, FaZe Clan)
2. **Independent Teams:** Amateur/casual teams owned directly by individual users

**Problem:** How to enforce this distinction at the database level to prevent invalid states?

**Invalid States to Prevent:**
- Team with BOTH organization AND owner set (violates single ownership principle)
- Team with NEITHER organization NOR owner set (orphaned team, no management authority)

**Business Rules:**
- Organization-owned teams: `organization` FK set, `owner` NULL
- Independent teams: `owner` FK set, `organization` NULL
- Exactly one ownership model per team (XOR relationship)

---

## Decision

**We will enforce Team ownership using a CheckConstraint with XOR logic.**

Implementation in `apps/organizations/models/team.py`:

```python
class Team(models.Model):
    organization = models.ForeignKey(
        'Organization',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Owning organization (NULL if independent team)"
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Owner user (NULL if organization-owned team)"
    )
    
    class Meta:
        db_table = 'organizations_team'
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(organization__isnull=False, owner__isnull=True) |
                    models.Q(organization__isnull=True, owner__isnull=False)
                ),
                name='team_has_organization_xor_owner',
                violation_error_message="Team must have organization XOR owner (not both, not neither)"
            )
        ]
```

**SQL Generated:**
```sql
ALTER TABLE "organizations_team" 
ADD CONSTRAINT "team_has_organization_xor_owner" 
CHECK (
  (("organization_id" IS NOT NULL AND "owner_id" IS NULL) OR 
   ("organization_id" IS NULL AND "owner_id" IS NOT NULL))
);
```

---

## Consequences

### Positive

✅ **Database-Level Enforcement:** Invalid states impossible at storage layer (cannot be created even via raw SQL)  
✅ **Clear Ownership Model:** No ambiguity in ownership hierarchy  
✅ **Simplifies Business Logic:** Service layer doesn't need redundant validation  
✅ **Audit Trail:** Constraint violations logged in database error messages  
✅ **Future-Proof:** Works with any ORM or database client

### Negative

❌ **Creation Flow Complexity:** Code must explicitly set one FK and ensure other is NULL  
❌ **Migration Risk:** If constraint logic incorrect, blocks all team creation (mitigated by testing in Phase 1)  
❌ **Error Message Quality:** Generic IntegrityError needs translation to user-friendly messages

### Neutral

🔶 **Performance:** CheckConstraint evaluated on INSERT/UPDATE (negligible overhead)  
🔶 **Database Dependency:** Constraint tied to PostgreSQL CHECK syntax (acceptable for this project)

---

## Alternatives Considered

### Alternative 1: Nullable FKs Without Constraint ❌

**Approach:** Make both `organization` and `owner` nullable without CheckConstraint.

**Pros:**
- Simpler initial implementation
- No constraint violation risk

**Cons:**
- **Invalid states possible:** Developer error could create team with both or neither
- **Service layer burden:** Every method must validate ownership manually
- **Data quality risk:** Bad data could accumulate over time

**Rejection Reason:** Database integrity too important to rely on application-layer validation alone.

---

### Alternative 2: Separate Models (OrganizationTeam, IndependentTeam) ❌

**Approach:** Create two separate Django models inheriting from abstract BaseTeam.

**Pros:**
- Impossible to have both ownership types (enforced by model structure)
- Clearer type distinction in code

**Cons:**
- **Duplicate code:** Most fields/methods identical between models
- **Query complexity:** Need UNION queries to get all teams
- **FK complications:** Other models would need GenericForeignKey to reference either team type
- **Migration nightmare:** Converting between types requires cross-table data movement

**Rejection Reason:** Code duplication and query complexity outweigh type safety benefits.

---

### Alternative 3: Single owner FK with is_organization Boolean Flag ❌

**Approach:** Single `owner` FK to User, add `owner_type` field ('USER' or 'ORGANIZATION').

**Pros:**
- Single FK simplifies schema
- Easy queries (no NULL checking)

**Cons:**
- **Type confusion:** Organization and User are different entities, FK should reflect that
- **FK integrity loss:** Cannot enforce Organization-specific constraints via DB FK
- **Misleading semantics:** User FK pointing to Organization feels wrong

**Rejection Reason:** Violates semantic clarity and loses FK relationship benefits.

---

## Implementation Notes

### Creation Patterns

**Organization-Owned Team:**
```python
team = Team.objects.create(
    name="Liquid Valorant",
    organization=liquid_org,  # FK set
    owner=None,               # Explicit NULL
    game_id=1,
    region="NA"
)
```

**Independent Team:**
```python
team = Team.objects.create(
    name="Weekend Warriors",
    organization=None,  # Explicit NULL
    owner=user,         # FK set
    game_id=1,
    region="NA"
)
```

### Validation Helper Method

Added to Team model:
```python
def clean(self):
    """Model-level validation (runs before save)."""
    if not self.organization and not self.owner:
        raise ValidationError("Team must have organization or owner")
    if self.organization and self.owner:
        raise ValidationError("Team cannot have both organization and owner")
```

### Testing

Test coverage in `apps/organizations/tests/test_team.py`:
- `test_create_organization_team()` - Verify org team creation succeeds
- `test_create_independent_team()` - Verify independent team creation succeeds
- `test_check_constraint_both_org_and_owner_set()` - Verify BOTH fails with IntegrityError
- `test_check_constraint_neither_org_nor_owner_set()` - Verify NEITHER fails with IntegrityError

---

## References

**Planning Documents:**
- [TEAM_ORG_ARCHITECTURE.md](../../../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_ARCHITECTURE.md) - Section 2.1 Database Strategy
- [TEAM_ORG_ENGINEERING_STANDARDS.md](../../../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_ENGINEERING_STANDARDS.md) - Section 3.3 Constraint Enforcement

**Related Code:**
- `apps/organizations/models/team.py` - Team model definition
- `apps/organizations/tests/test_team.py` - Constraint validation tests
- `apps/organizations/migrations/0001_initial.py` - Migration creating constraint

**Database Documentation:**
- [PostgreSQL CHECK Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-CHECK-CONSTRAINTS)
- [Django CheckConstraint](https://docs.djangoproject.com/en/5.2/ref/models/constraints/#checkconstraint)

---

**Last Updated:** 2026-01-25  
**Status:** Active - Constraint enforced in production migrations
