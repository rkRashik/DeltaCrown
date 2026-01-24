# ADR-003: Empire Score Calculation (Organization Rankings)

**Status:** ✅ Accepted  
**Date:** 2026-01-25  
**Deciders:** Engineering Team  
**Related Docs:** [TEAM_ORG_ARCHITECTURE.md](../../../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_ARCHITECTURE.md) §7.3 Organization Rankings

---

## Context

Organizations need a **ranking system** that reflects their competitive strength across multiple teams. Simply summing all team Crown Points (CP) creates perverse incentives:

**Problems with Simple Sum:**
1. **Spam Team Abuse:** Organizations could create 50 low-tier teams to inflate score
2. **Inactive Team Bloat:** Old/disbanded teams continue contributing to score
3. **No Roster Depth Reward:** Organization with 3 elite teams ranked same as one with 1 elite + 49 bronze teams

**Business Goals:**
- Reward organizations with **multiple competitive teams** (roster depth)
- Prevent gaming via spam teams
- Reflect **current** competitive strength (not historical)
- Encourage organizations to maintain quality over quantity

**Existing System:**
- Each team has `TeamRanking` with `current_cp` field
- Teams have `status` field (ACTIVE, DELETED, SUSPENDED, DISBANDED)
- Teams can be `temporary` (for special events, not part of core roster)

---

## Decision

**We will calculate Empire Score using the top 3 teams with weighted contributions: 1.0, 0.75, 0.5.**

**Filtering Rules:**
- ONLY include teams with `status='ACTIVE'` and `temporary=False`
- Ignore DELETED, SUSPENDED, DISBANDED teams
- Ignore temporary teams (tournament-specific squads)

**Formula:**
```
Empire Score = (Top Team CP × 1.0) + (2nd Team CP × 0.75) + (3rd Team CP × 0.5)
```

Implementation in `apps/organizations/models/ranking.py`:

```python
class OrganizationRanking(models.Model):
    organization = models.OneToOneField(
        'Organization',
        on_delete=models.CASCADE,
        primary_key=True
    )
    empire_score = models.IntegerField(default=0)
    
    def recalculate_empire_score(self) -> int:
        """
        Recalculate organization's Empire Score.
        
        Uses top 3 teams with weighted contributions:
        - 1st place: 100% (weight 1.0)
        - 2nd place: 75%  (weight 0.75)
        - 3rd place: 50%  (weight 0.5)
        
        Only counts ACTIVE, permanent teams (excludes temporary/event teams).
        """
        from apps.organizations.models import Team, TeamRanking
        
        # Get active, permanent teams only
        team_rankings = TeamRanking.objects.filter(
            team__organization=self.organization,
            team__status=TeamStatus.ACTIVE,
            team__temporary=False
        ).select_related('team').order_by('-current_cp')[:3]
        
        # Apply weighted scoring
        weights = [1.0, 0.75, 0.5]
        score = sum(
            int(ranking.current_cp * weight)
            for ranking, weight in zip(team_rankings, weights)
        )
        
        self.empire_score = score
        self.save(update_fields=['empire_score'])
        return score
```

---

## Consequences

### Positive

✅ **Prevents Spam Abuse:** Organizations can't inflate score with 50 bronze teams  
✅ **Rewards Depth:** Having 3 strong teams better than 1 elite + many weak  
✅ **Current State Focus:** Inactive teams automatically excluded  
✅ **Simple Logic:** Easy to explain to users, predictable results  
✅ **Performance Efficient:** Only queries top 3 teams, not entire roster

### Negative

❌ **Arbitrary Cutoff:** Why 3 teams? Why not 5? (See alternatives for rationale)  
❌ **Weight Tuning:** Weights (1.0, 0.75, 0.5) may need adjustment based on competitive data  
❌ **Recalculation Overhead:** Must recalculate whenever team CP changes (mitigated by async jobs)

### Neutral

🔶 **Organizations with <3 Teams:** Still ranked, just fewer contributions (fair)  
🔶 **Tie-Breaking:** Equal Empire Scores resolved by global_rank or timestamp (acceptable)

---

## Alternatives Considered

### Alternative 1: Sum All Team CP (No Limit) ❌

**Approach:** `Empire Score = Sum of all team CP`

**Pros:**
- Simplest calculation
- No cutoff decisions needed
- Rewards large organizations naturally

**Cons:**
- **Spam team abuse:** Create 100 teams to inflate score regardless of quality
- **No quality incentive:** 10 bronze teams (500 CP each) = 5000 score vs 1 elite team (5000 CP)
- **Inactive team bloat:** Old teams continue contributing

**Rejection Reason:** Creates perverse incentive to spam low-quality teams.

---

### Alternative 2: Top 5 Teams Weighted ❌

**Approach:** Use top 5 teams with weights [1.0, 0.9, 0.8, 0.7, 0.6]

**Pros:**
- Rewards deeper rosters
- More organizations have 5+ teams than 3+

**Cons:**
- **Complexity:** More weights to tune and explain
- **Diminishing returns unclear:** Why 0.9 and not 0.85?
- **Over-rewarding large orgs:** Big orgs with 5 teams dominate small orgs with 3 elite teams

**Rejection Reason:** Added complexity without clear business benefit. Top 3 sufficient for depth signal.

---

### Alternative 3: Time-Decayed Weighting ❌

**Approach:** Weight teams by recency of last match (newer = higher weight)

**Pros:**
- Rewards active teams over dormant ones
- Reflects "current" form more accurately

**Cons:**
- **Implementation complexity:** Requires tracking last_match_date, decay formula
- **Punishes off-season teams:** Team might be elite but inactive between tournaments
- **Unclear business value:** If team is ACTIVE and has high CP, it's competitive

**Rejection Reason:** Over-engineering. Simple status filter (ACTIVE) sufficient for "current" signal.

---

### Alternative 4: Average CP of All Teams ❌

**Approach:** `Empire Score = Average CP across all teams`

**Pros:**
- Rewards quality over quantity
- Can't game with spam teams (low CP teams hurt average)

**Cons:**
- **Disincentivizes roster growth:** Adding 4th team lowers score if below average
- **Punishes experimentation:** Can't have "development" teams without score penalty
- **Counterintuitive:** Users expect more teams = higher ranking

**Rejection Reason:** Disincentivizes having academy/development teams.

---

## Implementation Notes

### Recalculation Triggers

**When to Recalculate:**
1. **Team CP Changes:** After tournament/match updates team's CP
2. **Team Status Changes:** Team goes ACTIVE → DISBANDED or vice versa
3. **Team Joins/Leaves Org:** Organization acquires or releases team
4. **Periodic Recalc:** Nightly job to catch any missed updates

**Async Job (Phase 2+):**
```python
# In apps/organizations/tasks/ranking_tasks.py
@shared_task
def recalculate_org_empire_scores():
    """Nightly recalculation of all organization Empire Scores."""
    from apps.organizations.models import OrganizationRanking
    
    for ranking in OrganizationRanking.objects.select_related('organization').all():
        ranking.recalculate_empire_score()
```

### Signal-Based Updates

```python
# In apps/organizations/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=TeamRanking)
def update_org_empire_score_on_cp_change(sender, instance, **kwargs):
    """Update organization Empire Score when team CP changes."""
    team = instance.team
    if team.organization and team.status == TeamStatus.ACTIVE and not team.temporary:
        org_ranking = OrganizationRanking.objects.get(organization=team.organization)
        org_ranking.recalculate_empire_score()
```

### Testing

Test coverage in `apps/organizations/tests/test_ranking.py`:
- `test_recalculate_empire_score_with_teams()` - Top 3 weighted correctly
- `test_recalculate_empire_score_only_2_teams()` - Works with <3 teams
- `test_recalculate_empire_score_ignores_temporary_teams()` - Temporary teams excluded
- `test_recalculate_empire_score_ignores_inactive_teams()` - DISBANDED/DELETED excluded
- `test_empire_score_weights()` - Verify 1.0, 0.75, 0.5 multipliers

---

## Performance Considerations

### Query Optimization

**Current Query:**
```python
team_rankings = TeamRanking.objects.filter(
    team__organization=self.organization,
    team__status=TeamStatus.ACTIVE,
    team__temporary=False
).select_related('team').order_by('-current_cp')[:3]
```

**Index Required:**
- Composite index on `(team.organization_id, team.status, current_cp DESC)` for efficient filtering + sorting
- Already created in migration 0001_initial.py

**Query Complexity:** O(log N) for index scan + top 3 fetch (very fast, <5ms)

### Caching Strategy (Phase 3+)

```python
# Cache Empire Score for 15 minutes
from django.core.cache import cache

def get_empire_score(org_id: int) -> int:
    cache_key = f'org_empire_score:{org_id}'
    score = cache.get(cache_key)
    
    if score is None:
        ranking = OrganizationRanking.objects.get(organization_id=org_id)
        score = ranking.empire_score
        cache.set(cache_key, score, timeout=900)  # 15 min
    
    return score
```

---

## Future Considerations

### Weight Tuning Based on Data

After 6 months of production data:
- Analyze distribution of top 3 team CP across organizations
- If weights (1.0, 0.75, 0.5) create clustering, adjust (e.g., 1.0, 0.8, 0.6)
- Monitor for edge cases (organizations gaming weights)

### Multi-Game Empire Scores

If organizations compete in multiple games:
- Option 1: Separate Empire Score per game
- Option 2: Aggregate across games (all teams regardless of game)
- Current decision: Keep simple (single score), revisit if multi-game becomes common

---

## References

**Planning Documents:**
- [TEAM_ORG_ARCHITECTURE.md](../../../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_ARCHITECTURE.md) - Section 7.3 Organization Rankings
- [TEAM_ORG_PERFORMANCE_CONTRACT.md](../../../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_PERFORMANCE_CONTRACT.md) - Section 1.2 Leaderboard Performance

**Related Code:**
- `apps/organizations/models/ranking.py` - OrganizationRanking model
- `apps/organizations/tests/test_ranking.py` - Empire Score calculation tests
- `apps/organizations/signals.py` - Auto-recalculation triggers (Phase 2)

**Business Context:**
- Crown Point System documentation (docs/ranking/crown_point_system.md)
- Tournament placement rewards (docs/tournaments/reward_structure.md)

---

**Last Updated:** 2026-01-25  
**Status:** Active - Method implemented, signal-based updates in Phase 2
