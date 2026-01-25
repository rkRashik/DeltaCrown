# Hub Integration Contract - Phase C+

**Document Status:** STABLE API CONTRACT  
**Version:** 1.0  
**Last Updated:** 2026-01-26 16:00  
**Breaking Changes:** Require Phase D architecture review

---

## Purpose

This document defines the **STABLE API contract** between the vNext hub view (`vnext_hub`) and its data providers (helper functions, models, APIs). All contracts defined here are **LOCKED for Phase C+ and Phase D** consumption.

**Breaking changes to these contracts require explicit Phase D architecture review.**

---

## Hub View: `vnext_hub()`

**Route:** `/organizations/hub/`  
**Method:** GET only  
**Authentication:** Required (`@login_required`)  
**Template:** `teams/vnext_hub.html`

### Context Data Contract (STABLE)

The hub view **GUARANTEES** the following context variables:

| Key | Type | Required | Default | Notes |
|-----|------|----------|---------|-------|
| `page_title` | str | ✅ | 'Command Hub' | Always present |
| `featured_teams` | list[Team] | ✅ | `[]` | Empty list if no teams |
| `leaderboard_rows` | list[TeamRanking] | ✅ | `[]` | Empty list if no rankings |
| `available_games` | QuerySet[Game] | ✅ | `[]` | Empty queryset if no games |
| `selected_game` | str | ✅ | 'all' | Game slug or 'all' |
| `top_organization` | Organization \| None | ✅ | `None` | May be None |
| `user_teams_count` | int | ✅ | `0` | Never negative |
| `user_primary_team` | Team \| None | ✅ | `None` | May be None |
| `recent_tournament_winner` | dict \| None | ✅ | `None` | May be None |

**Empty State Guarantee:** All keys are present even if database is empty. No `KeyError` possible.

---

## Helper Function: `_get_hero_carousel_context()`

**Status:** STABLE API  
**Cache:** 2 minutes per user  
**Signature:** `_get_hero_carousel_context(request) -> dict`

### Return Value Contract (STABLE)

Returns `dict` with **GUARANTEED keys:**

```python
{
    'top_organization': Organization | None,  # Top org by empire_score (or None)
    'user_teams_count': int,                  # Count of user's active teams (0+)
    'user_primary_team': Team | None,         # User's primary team (or None)
    'recent_tournament_winner': dict | None   # Recent winner data (or None)
}
```

### `top_organization` Field Contract

**Type:** `Organization` object or `None`

**If present, guaranteed fields:**
- `org.name` (str)
- `org.slug` (str)
- `org.description` (str, may be empty)
- `org.logo_url` (str, may be empty)
- `org.is_verified` (bool)

**MAY be None:**
- `org.ranking` (OrganizationRanking) - Handle with `hasattr()` or `.ranking if hasattr(org, 'ranking') else None`
- `org.ceo` (User) - May be None if CEO not set

**Defensive Guard:** If org exists but `org.ranking` is None, no crash occurs. Template must check `{% if org.ranking %}`.

### `user_primary_team` Field Contract

**Type:** `Team` object or `None`

**If present, guaranteed fields:**
- `team.name` (str)
- `team.slug` (str)
- `team.logo_url` (str, may be empty)
- `team.status` (str, always 'ACTIVE' in this context)

**MAY be None:**
- `team.organization` (Organization) - Independent teams have None
- `team.ranking` (TeamRanking) - New teams may not have ranking yet

### `recent_tournament_winner` Field Contract

**Type:** `dict` or `None`

**If present, guaranteed keys:**
```python
{
    'team_name': str,         # Winner team name
    'team_slug': str,         # Winner team slug
    'tournament_name': str,   # Tournament name
    'tournament_id': int,     # Tournament ID
    'end_date': date          # Tournament end date
}
```

**If None:** No recent tournament found or tournaments app not available.

---

## Helper Function: `_get_featured_teams()`

**Status:** STABLE API  
**Cache:** 2 minutes (key: `featured_teams_{game_id}_{limit}`)  
**Signature:** `_get_featured_teams(game_id=None, limit=12) -> QuerySet[Team]`

### Return Value Contract (STABLE)

Returns `QuerySet[Team]` ordered by `-ranking__current_cp`.

**Empty State:** Returns empty QuerySet (`[]`) if no teams, never raises.

### Team Object Contract (When Iterating)

Each `Team` object **GUARANTEES:**
- `team.id` (int, primary key)
- `team.name` (str)
- `team.slug` (str)
- `team.logo_url` (str, may be empty)
- `team.status` (str, always 'ACTIVE' in this context)
- `team.get_absolute_url()` (returns canonical URL)

**MAY be None:**
- `team.organization` (Organization) - Independent teams have `None`
- `team.ranking` (TeamRanking) - New teams may not have ranking row yet

**GUARANTEED related querysets:**
- `team.memberships.all()` - May be empty but never None

**Defensive Handling:**
```python
# Template usage
{% for team in featured_teams %}
  {{ team.name }}  {# SAFE #}
  {% if team.organization %}{{ team.organization.name }}{% else %}Independent{% endif %}  {# SAFE #}
  {% if team.ranking %}{{ team.ranking.current_cp }} CP{% else %}Unranked{% endif %}  {# SAFE #}
{% empty %}
  <p>No featured teams yet.</p>
{% endfor %}
```

---

## Helper Function: `_get_leaderboard()`

**Status:** STABLE API  
**Cache:** 5 minutes (key: `hub_leaderboard_{game_id}_{limit}`)  
**Signature:** `_get_leaderboard(game_id=None, limit=50) -> list[TeamRanking]`

### Return Value Contract (STABLE)

Returns `list[TeamRanking]` (already evaluated, not QuerySet) ordered by `rank`.

**Empty State:** Returns empty list (`[]`) if no rankings, never raises.

### TeamRanking Object Contract

Each `TeamRanking` object **GUARANTEES:**
- `ranking.id` (int, primary key)
- `ranking.team` (Team, **NEVER None**)
- `ranking.rank` (int, 1-based)
- `ranking.current_cp` (int, 0+)
- `ranking.team.name` (str)
- `ranking.team.slug` (str)
- `ranking.team.get_absolute_url()` (canonical URL)

**MAY be None:**
- `ranking.team.organization` (Organization) - Independent teams have None

**Defensive Handling:**
```python
# Template usage
{% for ranking in leaderboard_rows %}
  #{{ ranking.rank }} - {{ ranking.team.name }} ({{ ranking.current_cp }} CP)
  {% if ranking.team.organization %}[{{ ranking.team.organization.abbreviation }}]{% endif %}
{% empty %}
  <p>Leaderboard not yet populated.</p>
{% endfor %}
```

---

## Data Requirements Summary

### What Hub Expects (REQUIRED)

**Minimum Viable Data:**
- At least 1 `Game` with `is_active=True` (for game filter dropdown)
- User must be authenticated (enforced by `@login_required`)

**Optional Data (Hub Gracefully Handles Missing):**
- Organizations (carousel shows placeholder if none)
- Teams (featured grid shows empty state)
- TeamRanking rows (leaderboard shows empty state)
- OrganizationRanking rows (top org fallback logic handles)
- Tournaments (carousel winner slide skipped if none)

### What Is Optional vs Required

| Data | Required? | Hub Behavior If Missing |
|------|-----------|------------------------|
| `Organization` records | ❌ Optional | Carousel shows "No top org" placeholder |
| `Team` records | ❌ Optional | Featured grid shows "No teams yet" |
| `TeamRanking` records | ❌ Optional | Leaderboard shows "Not yet populated" |
| `OrganizationRanking` records | ❌ Optional | Top org fallback skips ranking filter |
| `Game` records | ✅ Required | Filter dropdown empty (but no crash) |
| Authenticated user | ✅ Required | Enforced by `@login_required` |
| `TeamMembership` records | ❌ Optional | User carousel shows "No teams" |
| `Tournament` records | ❌ Optional | Winner slide skipped in carousel |

### Empty State Guarantees

**The hub is guaranteed crash-proof in these scenarios:**

1. **Empty Database:**
   - All helper functions return empty collections
   - All context keys present with default values
   - Template shows empty state messages

2. **Partial Data:**
   - Organization exists but no `OrganizationRanking` → No crash (fallback logic)
   - Team exists but no `TeamRanking` → Shows "Unranked"
   - Team exists but no `TeamMembership` → Shows empty roster

3. **Missing Related Objects:**
   - Team with `organization=None` → Shows "Independent"
   - Organization with `ceo=None` → CEO name omitted
   - Team with `owner=None` → Owner name omitted (rare)

4. **Legacy-Only Data:**
   - If only legacy teams exist (no vNext teams) → Featured grid empty
   - If only legacy orgs exist (no vNext orgs) → Top org empty
   - **Phase 5 dual-write ensures this scenario becomes less common over time**

---

## Breaking Change Policy

**Any change that breaks the contracts above requires:**

1. Phase D architecture review
2. Update to this document (new version)
3. Migration plan for existing consumers
4. Deprecation notice (if applicable)

**Examples of breaking changes:**
- Removing a guaranteed context key
- Changing a field from "always present" to "may be None"
- Changing return type of helper function
- Removing a model field that templates depend on

**Examples of non-breaking changes:**
- Adding new optional context keys (✅ ALLOWED)
- Adding new model fields (✅ ALLOWED)
- Improving performance (caching, query optimization) (✅ ALLOWED)
- Adding defensive guards (✅ ALLOWED)

---

## Widget API Contracts (Future)

**Status:** NOT YET STABLE (Phase D)

The following widgets are currently populated client-side via AJAX. Their API contracts will be formalized in Phase D:

- **Activity Ticker API** (`/api/organizations/hub/ticker/`)
- **Scout Radar API** (`/api/organizations/hub/scout-radar/`)
- **Scrims Board API** (`/api/organizations/hub/scrims/`)
- **Team Search API** (`/api/organizations/hub/search/`)

**Phase C+ State:** These endpoints exist but are not yet contract-locked. Breaking changes allowed until Phase D.

---

## Consumer Responsibilities

**Template Developers Must:**

1. **Always use `{% if %}` checks** for optional fields:
   ```django
   {% if team.organization %}
     {{ team.organization.name }}
   {% else %}
     Independent
   {% endif %}
   ```

2. **Always use `{% empty %}` in loops**:
   ```django
   {% for team in featured_teams %}
     {{ team.name }}
   {% empty %}
     <p>No teams yet.</p>
   {% endfor %}
   ```

3. **Never assume related objects exist** without checking:
   ```django
   {# BAD - crashes if team.ranking is None #}
   {{ team.ranking.current_cp }}
   
   {# GOOD - defensive #}
   {% if team.ranking %}{{ team.ranking.current_cp }} CP{% else %}Unranked{% endif %}
   ```

4. **Use `get_absolute_url()` for all team links**:
   ```django
   {# GOOD #}
   <a href="{{ team.get_absolute_url }}">{{ team.name }}</a>
   
   {# BAD - hardcoded URL (breaks routing strategy) #}
   <a href="/teams/{{ team.slug }}/">{{ team.name }}</a>
   ```

---

## Verification Checklist

**Before releasing hub changes:**

- [ ] All context keys documented in this contract are present
- [ ] All helper functions return correct types (even on empty DB)
- [ ] Template renders without errors on empty database
- [ ] Template renders without errors when related objects missing
- [ ] No hardcoded team URLs (all use `get_absolute_url()`)
- [ ] Defensive `{% if %}` checks for all optional fields
- [ ] Query budget ≤15 queries (verified with Django Debug Toolbar)
- [ ] Cache keys include all filter parameters (game_id, user_id)
- [ ] No silent behavior changes to existing contracts

---

**END OF HUB INTEGRATION CONTRACT**

**Next Review:** Phase D (when widget APIs are stabilized)
