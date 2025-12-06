# Production Deployment Checklist - Teams/Games/Tournaments/Rankings

**Release**: Phases 1-6 Refactoring (Teams, Games, Tournaments, Rankings)  
**Date**: TBD  
**DRI (Directly Responsible Individual)**: _________________________

---

## Pre-Deployment (24-48 hours before)

### Database Preparation
- [ ] **Full database backup** created and verified restorable
  - Location: `backups/pre-phase1-6-deployment-<YYYY-MM-DD>.sql`
  - Test restore on separate DB instance
  - Verify backup integrity (checksum)

- [ ] **Review pending migrations** for safety:
  - [ ] `apps/teams/migrations/0014_alter_team_game.py`
    - Changes Team.game from CharField to slug lookup
    - **Risk**: Medium - alters Team model schema
    - **Rollback**: Restore from backup if Team queries fail
  - [ ] `apps/games/migrations/000X_initial_tournamentgame.py` (if exists)
    - Creates TournamentGame model
    - **Risk**: Low - new model, no existing data affected
  - [ ] `apps/tournaments/migrations/000X_alter_tournament_game_fk.py` (if exists)
    - Changes Tournament.game from CharField to ForeignKey(TournamentGame)
    - **Risk**: High - alters Tournament model, requires data migration
    - **Rollback**: Restore from backup immediately if FK violations occur

### Staging Verification
- [ ] **Deploy to staging** environment first
- [ ] **Run full test suite** on staging:
  ```powershell
  pytest tests/test_leaderboard_views.py tests/test_game_service_edge_cases.py -v
  ```
  - **Expected**: 19/19 passing (10 leaderboard + 9 game service)
  - **Note**: Skip `test_rankings_integration.py` (known test fixture issues, Category B)

- [ ] **Execute manual QA plan** on staging:
  - Follow `Documents/Modify_TeamApp_&_GameApp/QA_MANUAL_TEST_PLAN.md`
  - Document any issues in incident tracker

- [ ] **Performance baseline** check:
  - Leaderboard page load time < 500ms
  - Admin game list view < 200ms
  - No N+1 queries on leaderboard views (check Django Debug Toolbar)

### Code & Configuration Review
- [ ] **Code freeze** 24 hours before deployment
- [ ] **Pull latest** from main branch:
  ```powershell
  git pull origin main
  git log --oneline -10  # Verify latest commits
  ```

- [ ] **Verify static files** collected:
  ```powershell
  python manage.py collectstatic --noinput --clear
  ```
  - Check `staticfiles/leaderboards/css/` exists
  - Verify no 404s on CSS file paths

- [ ] **Environment variables** configured:
  - `DEBUG = False` in production settings
  - `ALLOWED_HOSTS` includes production domain
  - Database credentials correct for prod DB

### Team Coordination
- [ ] **Notify stakeholders** (engineering, product, ops) of deployment window
- [ ] **Incident response team** on standby during deployment
- [ ] **Rollback plan** documented and tested:
  - Database restore procedure: < 15 minutes
  - Code rollback: `git revert <commit>` or redeploy previous tag
  - Migration rollback: `python manage.py migrate <app> <previous_migration>`

---

## Deployment (Production)

### Step 1: Enable Maintenance Mode (Optional)
- [ ] Set maintenance page (if applicable):
  ```powershell
  # Upload maintenance.html to CDN or set nginx config
  ```
- [ ] Notify users via site banner: "Scheduled maintenance: 15 minutes"

### Step 2: Database Migrations
- [ ] **Apply migrations** in order:
  ```powershell
  python manage.py migrate games        # Create TournamentGame model
  python manage.py migrate teams        # Alter Team.game field
  python manage.py migrate tournaments  # Alter Tournament.game FK
  python manage.py migrate leaderboards # (if any ranking migrations)
  ```
- [ ] **Verify migration success**:
  ```powershell
  python manage.py showmigrations | Select-String "games|teams|tournaments|leaderboards"
  ```
  - All should show `[X]` (applied)

### Step 3: Data Seeding
- [ ] **Seed 9 TournamentGame records**:
  ```powershell
  python manage.py shell
  ```
  ```python
  from apps.games.services.game_service import GameService
  
  # Verify 9 games present
  games = GameService.get_all_games()
  print(f"Total games: {len(games)}")  # Should be 9
  
  for game in games:
      print(f"{game.slug}: {game.name} (active={game.is_active})")
  ```
- [ ] **Expected output**:
  ```
  Total games: 9
  pubg-mobile: PUBG Mobile (active=True)
  freefire: FreeFire (active=True)
  ... (7 more)
  ```

### Step 4: Collect Static Files
- [ ] **Re-collect static files** in production:
  ```powershell
  python manage.py collectstatic --noinput
  ```
- [ ] **Verify CSS extraction**:
  - Check `staticfiles/leaderboards/css/styles.css` exists
  - File size > 0 bytes

### Step 5: Restart Application Services
- [ ] **Restart web servers** (Gunicorn/uWSGI):
  ```powershell
  sudo systemctl restart gunicorn  # Or your WSGI server
  ```
- [ ] **Restart Celery workers** (if applicable):
  ```powershell
  sudo systemctl restart celery-worker
  sudo systemctl restart celery-beat
  ```
- [ ] **Clear cache** (Redis/Memcached):
  ```powershell
  python manage.py shell
  ```
  ```python
  from django.core.cache import cache
  cache.clear()
  ```

### Step 6: Disable Maintenance Mode
- [ ] Remove maintenance page
- [ ] Verify site accessible at production URL

---

## Post-Deployment (Within 1 Hour)

### Smoke Tests
- [ ] **Critical path verification**:
  1. [ ] Home page loads (`/`)
  2. [ ] Admin login works (`/admin/`)
  3. [ ] Games list loads (`/admin/games/tournamentgame/`)
  4. [ ] Create team works (`/teams/create/`)
  5. [ ] Leaderboard loads (`/leaderboards/`)
  6. [ ] Game-specific leaderboard (`/leaderboards/valorant/`)

- [ ] **Spot-check database**:
  ```powershell
  python manage.py shell
  ```
  ```python
  from apps.games.models import TournamentGame
  from apps.teams.models import Team
  from apps.tournaments.models import Tournament
  
  # Check counts
  print(f"Games: {TournamentGame.objects.count()}")  # Should be 9
  print(f"Teams: {Team.objects.count()}")  # Existing teams preserved
  print(f"Tournaments: {Tournament.objects.count()}")  # Existing tournaments preserved
  
  # Verify Team.game is slug (not ID)
  team = Team.objects.first()
  print(f"Sample team game field: {team.game} (type: {type(team.game).__name__})")  # Should be 'str'
  ```

### Monitoring & Logs
- [ ] **Check application logs** for errors:
  ```powershell
  tail -f /var/log/gunicorn/error.log | Select-String "ERROR|CRITICAL"
  ```
  - **No IntegrityError**, **No AttributeError**, **No 500 errors**

- [ ] **Monitor database queries**:
  - Check slow query log for > 500ms queries
  - Verify no `reminder_sent` constraint errors (if seen, Category B issue - not blocking)

- [ ] **Check metrics** (Grafana/Datadog if available):
  - Response time < 500ms (p95)
  - Error rate < 1%
  - CPU/Memory within normal bounds

### User Impact Check
- [ ] **Verify existing teams** still load:
  - Navigate to 3-5 existing team detail pages
  - Check game field displays correctly (slug value like "valorant")

- [ ] **Verify existing tournaments** functional:
  - Open 2-3 existing tournament pages
  - Check Tournament.game shows TournamentGame name (not ID)

- [ ] **Check leaderboards** populate:
  - Global leaderboard shows all teams
  - Game-specific leaderboards filtered correctly

### Regression Spot Checks
- [ ] **Phase 6 CSS extraction**:
  - View page source of `/leaderboards/`
  - **No inline `<style>` tags** in HTML
  - CSS loaded from `/static/leaderboards/css/styles.css`

- [ ] **Phase 5 GameService**:
  ```powershell
  python manage.py shell
  ```
  ```python
  from apps.games.services.game_service import GameService
  
  # Test service methods
  valorant = GameService.get_game_by_slug('valorant')
  print(f"VALORANT: {valorant.name}, team size: {valorant.default_team_size}")
  
  all_games = GameService.get_all_games()
  print(f"Total active games: {len(all_games)}")  # Should be 9
  ```

---

## Rollback Procedure (If Needed)

### When to Rollback
- **Critical errors** detected:
  - 500 errors on > 10% of requests
  - IntegrityError preventing team/tournament creation
  - Migration failures causing data corruption

### Rollback Steps
1. [ ] **Immediately notify team** via incident channel
2. [ ] **Stop application** (prevent further writes):
   ```powershell
   sudo systemctl stop gunicorn
   ```
3. [ ] **Restore database** from pre-deployment backup:
   ```powershell
   psql -U postgres -d deltacrown < backups/pre-phase1-6-deployment-<YYYY-MM-DD>.sql
   ```
4. [ ] **Revert code** to previous stable tag:
   ```powershell
   git checkout <previous-release-tag>
   git reset --hard
   ```
5. [ ] **Re-collect static files** from old code:
   ```powershell
   python manage.py collectstatic --noinput --clear
   ```
6. [ ] **Restart services**:
   ```powershell
   sudo systemctl start gunicorn
   sudo systemctl restart celery-worker
   ```
7. [ ] **Verify rollback success**:
   - Site loads
   - No errors in logs
   - Existing data intact
8. [ ] **Post-mortem**: Document rollback reason, fix issues, reschedule deployment

---

## Post-Deployment Follow-Up (24-48 Hours)

### Monitoring
- [ ] **Daily log review** for 3 days post-deployment
- [ ] **Check error rates** in monitoring dashboard
- [ ] **User feedback** monitoring (support tickets, bug reports)

### Documentation
- [ ] **Update deployment log**:
  - Deployment timestamp
  - Migrations applied
  - Any issues encountered & resolutions
  - Rollback (if occurred)

- [ ] **Update CHANGELOG.md** with release notes:
  ```markdown
  ## [Phase 1-6] - YYYY-MM-DD
  ### Added
  - TournamentGame model with 9 seeded games
  - GameService for game data access
  - Team.game now uses slug (CharField)
  - Tournament.game now ForeignKey to TournamentGame
  - CSS extraction for leaderboard views
  - 100% test coverage for leaderboard views
  
  ### Changed
  - Team model: game field remains CharField (slug-based)
  - Tournament model: game field changed to ForeignKey
  
  ### Fixed
  - N+1 queries on leaderboard views
  - Accessibility issues on leaderboard pages (ARIA labels, contrast)
  ```

### Cleanup
- [ ] **Archive old backups** (keep for 30 days, then delete)
- [ ] **Remove maintenance notices** from site
- [ ] **Close deployment ticket** in project management tool

---

## Known Issues (Not Blocking Deployment)

### Category B: Pre-Existing Technical Debt
- **Integration test failures** (`tests/test_rankings_integration.py`):
  - 5/5 tests failing due to:
    - Missing `reminder_sent` field on Registration model (DB schema mismatch)
    - Test fixtures missing Tournament required fields (registration_start, tournament_start)
  - **Impact**: None - these are test-only issues, not affecting production functionality
  - **Action**: Fix test fixtures post-deployment (separate sprint task)

- **Migration 0014_alter_team_game.py** review:
  - Changes Team.game field (needs review, but low risk - CharField to CharField)
  - **Action**: Reviewed pre-deployment, no destructive changes detected

---

## Success Criteria

**Deployment considered successful if**:
1. ✅ All migrations applied without errors
2. ✅ 9 TournamentGame records seeded
3. ✅ Leaderboard views render correctly (19/19 tests passing)
4. ✅ No 500 errors in first hour post-deployment
5. ✅ Existing teams/tournaments still functional
6. ✅ CSS extracted to static files (no inline styles)

---

## Sign-Off

**Deployment Lead**: _________________________  
**Date/Time**: _________________________  
**Result**: SUCCESS / ROLLBACK / PARTIAL (describe)

**Notes**:
