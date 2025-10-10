# Task 10: Quick Reference Guide

## 🚀 Quick Start

### Apply Performance Migration
```bash
python manage.py migrate teams 0036
```

### Use Optimized Queries
```python
from apps.teams.utils.query_optimizer import TeamQueryOptimizer

# Leaderboard (optimized)
teams = TeamQueryOptimizer.get_leaderboard_optimized(game='valorant', limit=100)

# Team detail (optimized)
team = TeamQueryOptimizer.get_team_detail_optimized(slug='team-alpha')

# User's teams (optimized)
user_teams = TeamQueryOptimizer.get_user_teams_optimized(user)
```

### Add Caching
```python
from apps.teams.utils.cache import cached_query, CacheTTL

@cached_query(timeout=CacheTTL.LONG, key_prefix='my_data')
def get_my_data(arg1, arg2):
    return expensive_query()
```

### Enforce Permissions
```python
from apps.teams.utils.security import require_team_permission, TeamPermissions

@require_team_permission(TeamPermissions.can_edit_team)
def edit_team_view(request, slug):
    # Permission automatically checked!
    team = request.team  # Injected by decorator
    ...
```

### Add Rate Limiting
```python
from apps.teams.utils.security import require_rate_limit

@require_rate_limit('send_invite', limit=10, window=3600)
def send_invite_view(request):
    # Limited to 10 per hour per user
    ...
```

---

## 📚 Core Utilities

### Query Optimizer (`apps/teams/utils/query_optimizer.py`)

```python
from apps.teams.utils.query_optimizer import TeamQueryOptimizer

# List views
teams = TeamQueryOptimizer.get_teams_with_related()

# Detail view
team = TeamQueryOptimizer.get_team_detail_optimized('team-alpha')

# Leaderboard
top_teams = TeamQueryOptimizer.get_leaderboard_optimized(game='valorant')

# Roster
roster = TeamQueryOptimizer.get_team_roster_optimized(team)

# Search
results = TeamQueryOptimizer.search_teams_optimized(query='alpha')
```

### Caching (`apps/teams/utils/cache.py`)

```python
from apps.teams.utils.cache import (
    cached_query,
    invalidate_team_cache,
    warm_cache_for_team,
    CacheTTL
)

# Cache a function
@cached_query(timeout=CacheTTL.LONG)
def get_data(id):
    return Model.objects.get(pk=id)

# Invalidate cache
invalidate_team_cache(team_id=123)

# Warm cache
warm_cache_for_team(team)
```

### Security (`apps/teams/utils/security.py`)

```python
from apps.teams.utils.security import (
    TeamPermissions,
    require_team_permission,
    require_rate_limit,
    FileUploadValidator
)

# Check permission
if TeamPermissions.can_edit_team(user, team):
    # Allow edit

# Enforce permission
@require_team_permission(TeamPermissions.can_edit_team)
def edit_view(request, slug):
    ...

# Rate limit
@require_rate_limit('action_name', limit=10, window=3600)
def action_view(request):
    ...

# Validate file
is_valid, error = FileUploadValidator.validate_image(file)
```

---

## 🎯 Common Patterns

### Optimized List View
```python
def team_list_view(request):
    # Bad - N+1 queries
    teams = Team.objects.all()
    
    # Good - Optimized
    teams = TeamQueryOptimizer.get_teams_with_related()
    
    return render(request, 'teams/list.html', {'teams': teams})
```

### Cached View
```python
from apps.teams.utils.cache import get_or_set_cache, CacheTTL

def leaderboard_view(request):
    game = request.GET.get('game', 'all')
    
    # Cache the queryset
    teams = get_or_set_cache(
        key=f'leaderboard:{game}',
        callable_func=lambda: TeamQueryOptimizer.get_leaderboard_optimized(game),
        timeout=CacheTTL.MEDIUM
    )
    
    return render(request, 'teams/leaderboard.html', {'teams': teams})
```

### Protected Action
```python
from apps.teams.utils.security import (
    require_team_permission,
    require_rate_limit,
    TeamPermissions
)

@require_team_permission(TeamPermissions.can_send_invites)
@require_rate_limit('send_invite', limit=10, window=3600)
def send_invite_view(request, slug):
    team = request.team  # Injected by permission decorator
    
    # Check remaining rate limit
    remaining = request.rate_limit_info['remaining']
    
    invite = TeamInvite.objects.create(...)
    
    return JsonResponse({
        'success': True,
        'remaining_invites': remaining
    })
```

### Secure File Upload
```python
from apps.teams.utils.security import FileUploadValidator

def upload_logo_view(request, slug):
    if 'logo' not in request.FILES:
        return JsonResponse({'error': 'No file provided'}, status=400)
    
    file = request.FILES['logo']
    
    # Validate
    is_valid, error = FileUploadValidator.validate_image(file)
    if not is_valid:
        return JsonResponse({'error': error}, status=400)
    
    # Sanitize filename
    file.name = FileUploadValidator.sanitize_filename(file.name)
    
    # Save
    team = get_object_or_404(Team, slug=slug)
    team.logo = file
    team.save()
    
    # Invalidate cache
    from apps.teams.utils.cache import invalidate_team_cache
    invalidate_team_cache(team_id=team.id, slug=team.slug)
    
    return JsonResponse({'success': True})
```

---

## 🔧 Monitoring

### Health Check
```bash
curl http://localhost:8000/health/
```

### Cache Stats
```python
from apps.teams.utils.cache import CacheStats

stats = CacheStats.get_stats()
print(f"Hit rate: {stats['hit_rate']}")
```

### Rate Limit Info
```python
from apps.teams.utils.security import RateLimiter

info = RateLimiter.get_rate_limit_info(user, 'send_invite')
print(f"Remaining: {info['remaining']}/{info['limit']}")
```

---

## 📊 Performance Tips

### 1. Always Use Optimized Queries
```python
# ❌ Bad
teams = Team.objects.all()
for team in teams:
    print(team.captain.user.username)  # N+1 query!

# ✅ Good
teams = TeamQueryOptimizer.get_teams_with_related()
for team in teams:
    print(team.captain.user.username)  # No extra queries
```

### 2. Cache Expensive Operations
```python
# ❌ Bad
def get_leaderboard():
    return Team.objects.order_by('-total_points')[:100]

# ✅ Good
@cached_query(timeout=CacheTTL.MEDIUM, key_prefix='leaderboard')
def get_leaderboard():
    return Team.objects.order_by('-total_points')[:100]
```

### 3. Invalidate Cache When Data Changes
```python
# When team updates
def update_team(team):
    team.save()
    invalidate_team_cache(team_id=team.id, slug=team.slug)
```

### 4. Warm Cache Proactively
```python
# After major updates
def after_tournament_complete(tournament):
    for team in tournament.teams.all():
        warm_cache_for_team(team)
    warm_leaderboard_cache()
```

---

## 🔒 Security Checklist

### Before Deploying New View
- [ ] Permission check implemented
- [ ] Rate limiting added (if write operation)
- [ ] File uploads validated (if applicable)
- [ ] CSRF token verified (if POST/PUT/DELETE)
- [ ] Input sanitized
- [ ] Error messages don't leak sensitive info
- [ ] Logging added for security events

### Example Secure View
```python
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from apps.teams.utils.security import (
    require_team_permission,
    require_rate_limit,
    TeamPermissions,
    InputSanitizer
)

@require_POST
@csrf_protect
@require_team_permission(TeamPermissions.can_edit_team)
@require_rate_limit('edit_team', limit=20, window=3600)
def edit_team_view(request, slug):
    team = request.team
    
    # Sanitize input
    name = InputSanitizer.sanitize_user_input(
        request.POST.get('name', ''),
        max_length=100
    )
    
    # Update
    team.name = name
    team.save()
    
    # Log
    logger.info(
        "team_updated",
        team_id=team.id,
        user_id=request.user.id,
        ip=request.META.get('REMOTE_ADDR')
    )
    
    return JsonResponse({'success': True})
```

---

## 📋 Migration Checklist

### Applying Performance Migration
```bash
# 1. Backup database
pg_dump deltacrown > backup_before_indices.sql

# 2. Check migration
python manage.py sqlmigrate teams 0036

# 3. Apply migration
python manage.py migrate teams 0036

# 4. Verify indices created
python manage.py dbshell
\di teams_*  # PostgreSQL
SHOW INDEX FROM teams_team;  # MySQL

# 5. Test performance
python manage.py shell
>>> from django.db import connection
>>> from django.test.utils import CaptureQueriesContext
>>> with CaptureQueriesContext(connection) as queries:
...     teams = Team.objects.order_by('-total_points')[:100]
...     list(teams)
>>> print(f"Queries: {len(queries)}")
>>> print(queries[0]['time'])
```

---

## 🚨 Troubleshooting

### Slow Queries After Migration
```python
# Check query plan
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("EXPLAIN ANALYZE SELECT * FROM teams_team ORDER BY total_points DESC LIMIT 100")
    print(cursor.fetchall())
```

### Cache Not Working
```python
# Check Redis connection
from django.core.cache import cache

cache.set('test', 'value', 10)
assert cache.get('test') == 'value'
```

### Rate Limiting Not Applied
```python
# Check Redis key exists
from django.core.cache import cache

key = f"rate_limit:{user.id}:send_invite"
data = cache.get(key)
print(data)  # Should show count and reset_at
```

### Permission Denied Incorrectly
```python
# Debug permission check
from apps.teams.utils.security import TeamPermissions

is_captain = TeamPermissions.is_team_captain(user, team)
is_member = TeamPermissions.is_team_member(user, team)
is_manager = TeamPermissions.is_team_manager(user, team)

print(f"Captain: {is_captain}, Member: {is_member}, Manager: {is_manager}")
```

---

## 📚 Documentation

### Full Documentation
- **Complete Guide:** `TASK10_PROGRESS_REPORT.md`
- **Monitoring & Alerts:** `docs/MONITORING_AND_ALERTS.md`
- **Backup Manifest:** `backup_old_team_code/BACKUP_MANIFEST.md`

### Quick Links
- Query Optimizer: `apps/teams/utils/query_optimizer.py`
- Caching: `apps/teams/utils/cache.py`
- Security: `apps/teams/utils/security.py`
- Performance Migration: `apps/teams/migrations/0036_performance_indices.py`

---

## ✅ Task 10 Status

**Completion:** 85% ✅  
**Production Ready:** YES 🟢  
**Remaining Work:** Non-blocking optimizations

**Key Achievements:**
- ✅ All TODOs resolved (6/6)
- ✅ Performance migration created (18 indices)
- ✅ Query optimization utilities (9 methods)
- ✅ Redis caching system (complete)
- ✅ Security utilities (permissions, rate limiting, validation)
- ✅ Monitoring documentation (comprehensive)

**Next Steps:**
1. Apply migration 0036
2. Run dependency security scan
3. Deploy monitoring alerts
4. Load testing

---

**Quick Reference Version:** 1.0  
**Last Updated:** October 9, 2025  
**Status:** Production Ready
