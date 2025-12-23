# UP-M4 Changelog: Tournament & Team Stats Integration

## Date: December 23, 2025

### Summary
Integrated tournament and team data into UserProfileStats. Stats are now derived from source tables (Match, Tournament, Registration, Team) using deterministic, idempotent computation.

### Files Created
1. **apps/user_profile/services/tournament_stats.py** (TournamentStatsService)
   - `recompute_user_stats(user_id)`: Full stats recompute
   - `_compute_match_stats(user_id)`: Match wins/losses from Match model
   - `_compute_tournament_stats(user_id)`: Tournament participation from Registration/Result
   - `_compute_team_stats(user_id)`: Team membership from TeamMembership
   - `get_user_tournament_history(user_id)`: Detailed tournament history

2. **apps/user_profile/management/commands/recompute_user_stats.py**
   - Dry-run mode: `--dry-run`
   - Limit mode: `--limit N`
   - Single user: `--user-id ID`
   - Full recompute: no flags

3. **apps/user_profile/tests/test_tournament_stats.py** (10 tests)
   - Stats derivation from source tables
   - Idempotency tests
   - Edge cases (no data, deterministic results)

### Test Results
```
pytest apps/user_profile/tests/ --tb=no
61 collected, 61 passed, 0 failed
```

**Breakdown:**
- UP-M0: 0 tests
- UP-M1: 9 tests (public_id system)
- UP-M2: 31 tests (activity log, stats, backfill)
- UP-M3: 11 tests (economy sync, signal, reconcile)
- UP-M4: 10 tests (tournament/team stats derivation)

### Architecture Principles
1. **SOURCE OF TRUTH**:
   - Match model (matches_played, matches_won)
   - Registration + TournamentResult (tournaments_played, tournaments_won, tournaments_top3)
   - TeamMembership (teams_joined, current team)

2. **DERIVED DATA**:
   - UserProfileStats (read model, never manually updated)
   - Always recomputable from source tables
   - Deterministic (same input → same output)

3. **IDEMPOTENCY**:
   - Safe to call recompute multiple times
   - No side effects
   - Audit trail preserved in source tables

### Stats Computed
- `matches_played`: Count of completed matches (Match.state = COMPLETED/FORFEIT)
- `matches_won`: Count of won matches (Match.winner_id = user's registration)
- `tournaments_played`: Count of confirmed registrations
- `tournaments_won`: Count of 1st place finishes (TournamentResult.placement = 1)
- `tournaments_top3`: Count of top 3 finishes (TournamentResult.placement <= 3)
- `teams_joined`: Count of active team memberships
- Timestamps: first_tournament_at, last_tournament_at, last_match_at

### Management Command
```bash
# Dry-run (no changes)
python manage.py recompute_user_stats --dry-run

# Recompute up to 100 users
python manage.py recompute_user_stats --limit 100

# Recompute specific user
python manage.py recompute_user_stats --user-id 42

# Recompute all users
python manage.py recompute_user_stats
```

### Integration Points
- Stats service is standalone (no signals yet)
- Manual trigger via management command
- Can be called from admin actions or scheduled tasks
- Future: Add signals for real-time updates (match complete, tournament end)

### Notes
- No migrations needed (UserProfileStats already exists from UP-M2)
- No schema changes required
- Stats are computed on-demand (not auto-updated by signals yet)
- Team stats use TeamMembership.Status.ACTIVE (not TeamMembership.ACTIVE)
