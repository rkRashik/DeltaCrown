# UP-PHASE9B: Performance & Query Budget Audit

**Phase:** Post-Launch Readiness  
**Type:** Performance Analysis & Budget Definition  
**Date:** 2025-12-29  
**Status:** Analysis Document

---

## Executive Summary

This document audits the **query patterns** and **performance characteristics** of the user_profile system's two main pages: Profile Public Page and Settings Page. It defines query budgets, identifies N+1 risks, and proposes privacy-aware caching strategies.

**Goal:** Ensure user_profile system performs well at scale (1000+ requests/minute).

---

## 1. Current Query Analysis

### 1.1 Profile Public Page (`profile_public_v2`)

**File:** `apps/user_profile/views/fe_v2.py` (lines 34-219)

**Query Path Analysis:**

#### Query 1-2: User & Profile Lookup
```python
# Line 70: User.objects.get(username=username)
# Line 71: UserProfile.objects.get(user=profile_user)
```
**Count:** 2 queries  
**Optimizable:** No (necessary lookups)

#### Query 3: Privacy Settings
```python
# ProfilePermissionChecker.__init__ (profile_permissions.py line 36)
# PrivacySettings.objects.get_or_create(user_profile=profile)
```
**Count:** 1-2 queries (1 if exists, 2 if create)  
**Optimizable:** Yes (cache or prefetch)

#### Query 4: Follow Status
```python
# Line 77: ProfilePermissionChecker checks FollowService.is_following()
# FollowService.is_following() → Follow.objects.filter(...).exists()
```
**Count:** 1 query  
**Optimizable:** Yes (can be combined with other queries)

#### Query 5-8: Game Passports
```python
# Line 113: GamePassportService.get_all_passports(user=profile_user)
# Internally queries:
# - GameProfile.objects.filter(user=profile_user)
# - GameProfileConfig.objects.filter(game=passport.game)  # Per passport
# - Team lookups if passport has current_team (N+1 risk)
```
**Count:** 1 base query + N queries per passport (N+1 RISK)  
**Optimizable:** Yes (select_related for game, current_team)

#### Query 9: Teams
```python
# Line 128: TeamMembership.objects.filter(user=profile_user).select_related('team').first()
```
**Count:** 1 query  
**Optimizable:** Already optimized (select_related)

#### Query 10: Follower/Following Counts
```python
# Line 209: Follow.objects.filter(following=profile_user).count()
# Line 210: Follow.objects.filter(follower=profile_user).count()
```
**Count:** 2 queries  
**Optimizable:** Yes (annotate on UserProfile, or cache)

#### Context Builder Queries (build_public_profile_context)

**Query 11: User Lookup (Duplicate)**
```python
# profile_context.py line 78: User.objects.get(username=username)
```
**Count:** 1 query (DUPLICATE - already fetched in view)  
**Optimizable:** Yes (pass user object instead of username)

**Query 12: Profile Lookup (Duplicate)**
```python
# profile_context.py line 84: get_user_profile_safe(target_user)
```
**Count:** 1 query (DUPLICATE)  
**Optimizable:** Yes (reuse from view)

**Query 13: Stats**
```python
# profile_context.py line 212: UserProfileStats.objects.get(user_profile=profile)
```
**Count:** 1 query  
**Optimizable:** Yes (prefetch_related or cache)

**Query 14-15: Activity Feed**
```python
# profile_context.py line 265/278: UserActivity.objects.filter(...).order_by('-created_at')[:10]
```
**Count:** 1-2 queries (depends on is_owner)  
**Optimizable:** No (always need fresh activity)

**Query 16+: Social Links**
```python
# profile_context.py line 355: SocialLink.objects.filter(user=profile.user)
```
**Count:** 1 query  
**Optimizable:** Yes (prefetch_related)

#### **TOTAL QUERY COUNT (Current State):**
- **Minimum:** 15 queries (no game passports, follow check cached)
- **Typical:** 20-25 queries (3 game passports with teams)
- **Worst Case:** 35+ queries (10 game passports with teams, no caching)

#### **N+1 Risks Identified:**
1. ✅ **Game Passport Teams** - Already uses `select_related('team')` (line 128, 180)
2. ⚠️ **Game Passport Game Configs** - May query per passport
3. ⚠️ **Duplicate User/Profile Lookups** - View and context builder both query

---

### 1.2 Settings Page (`profile_settings_v2`)

**File:** `apps/user_profile/views/fe_v2.py` (lines 277-320)

**Query Path Analysis:**

#### Query 1: User (Implicit)
```python
# @login_required decorator ensures request.user is loaded
```
**Count:** 0 (already in session)

#### Query 2: Profile Lookup
```python
# Line 298: build_public_profile_context(viewer=request.user, username=request.user.username)
# Internally: UserProfile.objects.get(user=request.user)
```
**Count:** 1 query  
**Optimizable:** Yes (cache on session or use select_related)

#### Query 3: Privacy Settings
```python
# Context builder loads PrivacySettings
```
**Count:** 1 query  
**Optimizable:** Yes (prefetch_related)

#### Query 4: Notification Preferences
```python
# GET /me/settings/notifications/ endpoint
# NotificationPreferences.objects.get(user_profile=profile)
```
**Count:** 1 query (if user clicks notifications tab)  
**Optimizable:** Yes (lazy load on tab open)

#### Query 5: Wallet Settings
```python
# GET /me/settings/wallet/ endpoint
# WalletSettings.objects.get(user_profile=profile)
```
**Count:** 1 query (if user clicks wallet tab)  
**Optimizable:** Yes (lazy load on tab open)

#### Query 6: Game Passports
```python
# If user opens passport section
# GameProfile.objects.filter(user=request.user)
```
**Count:** 1 query  
**Optimizable:** Yes (lazy load)

#### **TOTAL QUERY COUNT (Settings Page):**
- **Initial Load:** 3-5 queries (profile, privacy, basic context)
- **Full Interaction:** 8-10 queries (all tabs opened)
- **Per Save:** 2-3 queries (update + audit log)

**Status:** ✅ Settings page is well-optimized (already uses lazy loading via AJAX)

---

## 2. Query Budget Targets

### 2.1 Profile Public Page Budget

**Target (Launch):**
- ≤20 queries per page load (cold cache)
- ≤10 queries per page load (warm cache)

**Critical Threshold:** >25 queries (alert)

**Rationale:** Profile page is high-traffic (public-facing), must scale.

### 2.2 Settings Page Budget

**Target (Launch):**
- ≤15 queries initial load
- ≤5 queries per settings save

**Critical Threshold:** >20 queries initial load (alert)

**Rationale:** Settings page is owner-only (lower traffic), but should still be fast.

### 2.3 Admin Panel Budget

**Target:**
- ≤50 queries per changelist page (acceptable for admin)
- ≤30 queries per detail page

**Critical Threshold:** >100 queries (alert, indicates missing select_related)

**Rationale:** Admin panel is staff-only, performance less critical than public pages.

---

## 3. Optimization Opportunities

### 3.1 High-Impact Optimizations

#### 1. Eliminate Duplicate User/Profile Queries

**Problem:** View and context builder both query same data

**Solution:**
```python
# apps/user_profile/views/fe_v2.py (CONCEPTUAL - NOT IMPLEMENTED)
def profile_public_v2(request, username):
    # Fetch once
    profile_user = User.objects.get(username=username)
    user_profile = UserProfile.objects.select_related('user').get(user=profile_user)
    
    # Pass objects instead of username
    context = build_public_profile_context_optimized(
        viewer=request.user,
        profile_user=profile_user,  # Pass object
        user_profile=user_profile,  # Pass object
        requested_sections=[...]
    )
```

**Impact:** -2 queries per page load

---

#### 2. Prefetch Game Passports with select_related

**Problem:** Game Passport queries may not optimize for related data

**Solution:**
```python
# apps/user_profile/services/game_passport_service.py (CONCEPTUAL)
def get_all_passports(user):
    return GameProfile.objects.filter(user=user).select_related(
        'game',           # Game model
        'current_team',   # Team model
        'user_profile'    # UserProfile (if needed)
    ).prefetch_related(
        'game__gameprofileconfig_set'  # Config per game
    )
```

**Impact:** -5 to -10 queries per page load (if 5-10 passports)

---

#### 3. Annotate Follower/Following Counts on UserProfile

**Problem:** Two separate COUNT queries every page load

**Solution:**
```python
# apps/user_profile/models_main.py (CONCEPTUAL)
class UserProfile(models.Model):
    # ... existing fields
    
    # Cached counts (updated via signals)
    follower_count = models.PositiveIntegerField(default=0)
    following_count = models.PositiveIntegerField(default=0)
    
    # Signal handler (apps/user_profile/signals/follow_signals.py)
    # Update counts when Follow.objects.create() or .delete()
```

**Impact:** -2 queries per page load

---

#### 4. Cache UserProfileStats

**Problem:** Stats rarely change, but queried every page load

**Solution:**
```python
# apps/user_profile/services/profile_context.py (CONCEPTUAL)
from django.core.cache import cache

def _build_stats_data(profile):
    cache_key = f"profile_stats:{profile.id}"
    stats = cache.get(cache_key)
    
    if not stats:
        stats_obj = UserProfileStats.objects.get(user_profile=profile)
        stats = {
            'tournaments_played': stats_obj.tournaments_played,
            # ... other fields
        }
        cache.set(cache_key, stats, timeout=3600)  # 1 hour
    
    return stats
```

**Impact:** -1 query per page load (warm cache)

---

### 3.2 Medium-Impact Optimizations

#### 5. Lazy Load Activity Feed

**Problem:** Activity feed queried even if user doesn't scroll to it

**Solution:** Use Intersection Observer API to load when visible

**Impact:** -1 query for users who don't scroll down

---

#### 6. Prefetch Social Links

**Problem:** Social links queried separately

**Solution:**
```python
# apps/user_profile/views/fe_v2.py (CONCEPTUAL)
user_profile = UserProfile.objects.select_related('user').prefetch_related('user__sociallink_set').get(...)
```

**Impact:** -1 query per page load

---

### 3.3 Low-Impact Optimizations

#### 7. Cache Privacy Settings

**Rationale:** Privacy settings change rarely (user updates ~1/month)

**Solution:** Cache PrivacySettings with 1-hour TTL

**Impact:** -1 query per page load (warm cache)

---

## 4. What Should NEVER Be Cached

### 4.1 Privacy-Sensitive Data

**DO NOT Cache:**
- ❌ `can_view_*` permission flags (viewer-dependent)
- ❌ Follow relationships (changes frequently)
- ❌ Profile visibility settings (privacy risk if stale)
- ❌ Wallet balances (economy data must be real-time)
- ❌ Activity feed (time-sensitive)

**Rationale:** Stale privacy data = potential data leak

---

### 4.2 User-Specific Data

**DO NOT Cache Across Users:**
- ❌ Profile context for different viewers (owner sees different data than visitor)
- ❌ Permission checks (different for each viewer)

**Rationale:** Cache poisoning risk (UserA sees UserB's private data)

---

### 4.3 Frequently Changing Data

**DO NOT Cache:**
- ❌ Follower/following counts (unless using cached column + signals)
- ❌ Game Passport LFT status (changes frequently)
- ❌ Online status (if implemented)

---

## 5. Safe Caching Strategies

### 5.1 User-Scoped Caching (Safe)

**Cache Key Pattern:**
```python
cache_key = f"profile:{profile_id}:viewer:{viewer_id or 'anon'}:section:{section}"
```

**Example:**
```python
# Owner view
cache.set('profile:123:viewer:123:stats', stats_data, 300)  # 5 min

# Visitor view
cache.set('profile:123:viewer:456:stats', stats_data, 300)

# Anonymous view
cache.set('profile:123:viewer:anon:stats', stats_data, 300)
```

**Invalidation:** Clear cache on profile update

---

### 5.2 Public Data Caching (Safe)

**What Can Be Cached:**
- ✅ Public profile fields (display_name, bio, avatar URL)
- ✅ Public stats (tournaments_played, matches_won)
- ✅ Public achievements (if `show_achievements=True`)

**TTL:** 5-15 minutes (balance freshness vs query reduction)

---

### 5.3 Fragment Caching (Template-Level)

**Django Template Caching:**
```django
{% load cache %}

<!-- Safe: Public stats card -->
{% cache 300 profile_stats profile.id %}
    <div class="stat-card">
        <span>{{ stats.tournaments_played }}</span>
        <span>Tournaments</span>
    </div>
{% endcache %}
```

**Rationale:** Template rendering is expensive (HTML generation)

---

## 6. Performance Budget Summary

| Page/Endpoint | Cold Cache | Warm Cache | Critical | Status |
|---------------|------------|------------|----------|--------|
| Profile Public | 20 queries | 10 queries | 25 queries | ⚠️ Needs optimization |
| Settings Page | 15 queries | 8 queries | 20 queries | ✅ Acceptable |
| Settings Save | 5 queries | 3 queries | 10 queries | ✅ Acceptable |
| Admin Changelist | 50 queries | 30 queries | 100 queries | ✅ Acceptable |

**Legend:**
- ✅ Acceptable: Meets target
- ⚠️ Needs optimization: Exceeds target in worst case

---

## 7. Monitoring Plan

### 7.1 Query Count Monitoring

**Tool:** Django Debug Toolbar (dev) + django-silk (staging/prod)

**Metrics to Track:**
- Queries per request (avg, P95, P99)
- Duplicate queries (same SQL executed >1 time)
- Slow queries (>100ms)

**Alerts:**
- Profile page >25 queries (warning)
- Settings page >20 queries (warning)
- Any endpoint >50 queries (critical)

---

### 7.2 Database Load Monitoring

**Metrics:**
- Connection pool usage (%)
- Active queries
- Query latency (ms)
- Replication lag (if using read replicas)

**Thresholds:**
- Connection pool >80%: Scale vertically or add read replicas
- Query latency P95 >500ms: Optimize indexes or queries

---

## 8. Recommended Optimizations (Priority Order)

### Priority 1 (Pre-Launch)
1. ✅ **Eliminate duplicate User/Profile queries** (-2 queries)
2. ✅ **Prefetch Game Passports with select_related** (-5 to -10 queries)
3. ✅ **Cache follower/following counts** (-2 queries)

**Expected Impact:** Profile page: 25 queries → 15 queries (33% reduction)

---

### Priority 2 (First Month)
4. Cache UserProfileStats (1-hour TTL)
5. Prefetch Social Links
6. Implement query count monitoring

**Expected Impact:** Profile page: 15 queries → 12 queries (additional 20% reduction)

---

### Priority 3 (As Needed)
7. Lazy load activity feed (Intersection Observer)
8. Fragment caching for stats cards
9. Database read replica for profile views

---

## 9. Scaling Considerations

### 9.1 Traffic Estimates

**Launch Estimates:**
- 100 concurrent users
- 10 profile views/second
- 2 settings updates/second

**1 Year Growth:**
- 1,000 concurrent users
- 100 profile views/second
- 20 settings updates/second

### 9.2 Database Scaling Strategy

**Phase 1 (Launch):** Single PostgreSQL instance
- Expected: Handle 100 requests/second comfortably
- Cost: $50-100/month (managed Postgres)

**Phase 2 (1,000 users):** Add read replicas
- Route profile views to read replica
- Write operations (settings saves) to primary
- Cost: +$50/month per replica

**Phase 3 (10,000 users):** Redis caching layer
- Cache public profile data
- Cache stats, achievements
- Cost: +$30/month (managed Redis)

---

## 10. Implementation Checklist

**Before Launch:**
- [ ] Audit current query counts (use django-debug-toolbar)
- [ ] Implement Priority 1 optimizations
- [ ] Add query count monitoring
- [ ] Set up alerts for query budget violations

**After Launch (First Week):**
- [ ] Monitor query patterns with real traffic
- [ ] Identify slowest queries (>500ms)
- [ ] Validate cache hit rates (if caching implemented)

**After Launch (First Month):**
- [ ] Implement Priority 2 optimizations
- [ ] Review scaling strategy based on traffic
- [ ] Consider read replica if query load high

---

## 11. Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **N+1 queries at scale** | High | Medium | Prefetch_related monitoring |
| **Cache poisoning** | Critical | Low | User-scoped cache keys only |
| **Stale privacy data** | Critical | Low | Never cache permission flags |
| **Database overload** | High | Low | Query budget monitoring + alerts |

---

## Final Recommendations

**Launch Decision:**
- ✅ **System is safe to launch** with current query patterns
- Current 20-25 queries/page is acceptable for launch scale (100 users)
- Priority 1 optimizations should be implemented within first month

**Critical Actions:**
1. Eliminate duplicate queries (easy win, big impact)
2. Set up query count monitoring (visibility)
3. Plan for read replica if traffic grows beyond 500 concurrent users

---

**Document Version:** 1.0  
**Last Updated:** 2025-12-29  
**Status:** Analysis Document - No Implementation Required  
**Owner:** Backend Engineering Team
