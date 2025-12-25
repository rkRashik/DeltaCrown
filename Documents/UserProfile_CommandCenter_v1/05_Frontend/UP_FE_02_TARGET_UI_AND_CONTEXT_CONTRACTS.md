# UP-FE-02: TARGET UI AND CONTEXT CONTRACTS

**Project:** DeltaCrown User Profile — Frontend Cleanup  
**Phase:** Target Architecture Definition (TEMPLATES-FIRST)  
**Date:** 2025-01-XX  
**Prerequisites:** UP_FE_01_FRONTEND_AUDIT.md completed

---

## 1. DESIGN PRINCIPLES

### 1.1 Core Constraints
- **TEMPLATES-FIRST:** Django Templates + Tailwind CSS + Vanilla JS (NO React/Next/Vue)
- **SSR-BY-DEFAULT:** Pages must work without JavaScript (progressive enhancement)
- **PRIVACY-BY-DEFAULT:** Use `get_visible_profile(user, viewer)` helper everywhere
- **AUDIT-AWARE:** All mutations write `UserAuditEvent` via `AuditService`
- **SERVICE-LAYER-ENFORCED:** Views call services, never ORM directly
- **OFFLINE-FIRST:** No CDN dependencies (bundle Alpine.js if used)
- **PUBLIC_ID-ROUTING:** Use `<public_id>` in URLs, not `<username>` (prevent enumeration)

### 1.2 Tech Stack
```
BACKEND:   Django 5.2.8 + PostgreSQL
FRONTEND:  Django Templates + Tailwind CSS 3.x + Vanilla JS
STATE:     Server-side (Django context) + minimal client-side (Alpine.js for interactions)
FORMS:     Django Forms + HTMX for AJAX (optional) OR Vanilla JS fetch()
STYLING:   Tailwind utility classes + custom CSS for complex components
ICONS:     Heroicons (inline SVG) or Font Awesome (self-hosted)
```

---

## 2. PAGE ARCHITECTURE

### 2.1 Required Pages (6 Pages)
```
1. /profile/<public_id>/          Public Profile (universal)
2. /me/                           Owner Dashboard (authenticated)
3. /me/settings/                  Unified Settings (authenticated)
4. /me/economy/                   Wallet + Transactions (authenticated)
5. /me/activity/                  Activity Log (authenticated)
6. /me/stats/                     Computed Stats (authenticated)
```

### 2.2 Legacy Routes (Redirects Only)
```
/@<username>/       → 301 redirect to /profile/<public_id>/
/u/<username>/      → 301 redirect to /profile/<public_id>/
/<username>/        → 301 redirect to /profile/<public_id>/
/me/edit/           → 301 redirect to /me/settings/
```

### 2.3 API Endpoints (Unchanged)
```
/api/profile/<public_id>/         GET profile JSON
/api/profile/follow/              POST follow user
/api/profile/unfollow/            POST unfollow user
/actions/update-bio/              POST update bio (AJAX)
/actions/add-social-link/         POST add social (AJAX)
/actions/add-game-profile/        POST add game ID (AJAX)
/actions/edit-game-profile/       POST edit game ID (AJAX)
/actions/delete-game-profile/     POST delete game ID (AJAX)
```

---

## 3. PAGE SPECIFICATIONS

### 3.1 PAGE 1: `/profile/<public_id>/` (Public Profile)
**Purpose:** Display user profile to public or authenticated users (with privacy enforcement)

#### 3.1.1 Route
```python
# apps/user_profile/urls.py
path('profile/<str:public_id>/', views.public_profile_view, name='profile'),
```

#### 3.1.2 View Signature
```python
def public_profile_view(request: HttpRequest, public_id: str) -> HttpResponse:
    """
    Display public profile with privacy enforcement.
    Uses get_visible_profile() helper to respect privacy settings.
    Writes PROFILE_VIEWED audit event if authenticated.
    """
```

#### 3.1.3 Context Contract
```python
{
    # Core Identity
    'profile': UserProfile,          # FILTERED via get_visible_profile()
    'user': User,                    # Minimal fields only (username, date_joined)
    'is_own_profile': bool,
    'is_private': bool,              # True if profile.is_private AND viewer != owner
    
    # Stats (conditional on privacy)
    'follower_count': int,           # Visible if not is_private
    'following_count': int,          # Visible if not is_private
    'is_following': bool,            # Only if request.user.is_authenticated
    
    # Game Data (conditional)
    'game_profiles': List[dict],     # FILTERED via privacy settings
    'achievements': List[Achievement],  # FILTERED
    'recent_matches': List[Match],   # FILTERED
    
    # Economy (owner-only)
    'wallet': DeltaCrownWallet | None,  # Only if is_own_profile
    
    # Social Links (conditional)
    'social_links': List[dict],      # Only if profile.show_socials OR is_own_profile
    
    # Teams & Memberships (conditional)
    'active_teams': List[Team],      # FILTERED via privacy
    
    # Metadata
    'page_title': str,               # "ProfileName (@username)"
    'og_image': str,                 # profile.avatar.url or default
}
```

#### 3.1.4 Privacy Enforcement Rules
```python
# RULE 1: If profile.is_private AND viewer != owner → Minimal Card
if profile.is_private and not is_own_profile:
    return render('user_profile/profile_private.html', {
        'profile': profile,  # Only: avatar, display_name, username
        'is_private': True,
    })

# RULE 2: Field-level visibility (checked in template)
social_links = [] if not profile.show_socials and not is_own_profile else fetch_social_links()
real_name = profile.real_full_name if profile.show_real_name or is_own_profile else None
email = user.email if profile.show_email or is_own_profile else None
```

#### 3.1.5 Template Structure
```django
{# templates/user_profile/profile.html #}
{% extends "base.html" %}

{% block content %}
<div class="profile-container">
    {% include "user_profile/components/hero_banner.html" %}
    {% include "user_profile/components/identity_card.html" %}
    {% include "user_profile/components/stats_panel.html" %}
    {% include "user_profile/components/game_profiles.html" %}
    {% include "user_profile/components/recent_activity.html" %}
    
    {% if is_own_profile %}
        {% include "user_profile/components/wallet_preview.html" %}
    {% endif %}
</div>
{% endblock %}
```

#### 3.1.6 Components (Partials)
```
components/hero_banner.html       Avatar + banner + follow button
components/identity_card.html     Display name + bio + metadata
components/stats_panel.html       Followers, matches, achievements counts
components/game_profiles.html     Valorant, eFootball, etc. game IDs
components/recent_activity.html   Last 5 matches or achievements
components/wallet_preview.html    Balance + currency (owner-only)
```

---

### 3.2 PAGE 2: `/me/` (Owner Dashboard)
**Purpose:** Personalized dashboard for authenticated user (overview of all modules)

#### 3.2.1 Route
```python
path('me/', views.owner_dashboard_view, name='dashboard'),
```

#### 3.2.2 View Signature
```python
@login_required
def owner_dashboard_view(request: HttpRequest) -> HttpResponse:
    """
    Owner-only dashboard. Shows profile status, quick stats, recent activity.
    Uses services: TournamentStatsService, EconomySyncService.
    Writes DASHBOARD_VIEWED audit event.
    """
```

#### 3.2.3 Context Contract
```python
{
    # Core
    'profile': UserProfile,
    
    # Stats (from UserProfileStats model)
    'stats': {
        'total_tournaments': int,
        'total_matches': int,
        'total_wins': int,
        'total_earnings': Decimal,
        'win_rate': float,           # stats.win_rate property
        'avg_placement': float,      # stats.avg_placement property
    },
    
    # Economy (from EconomySyncService)
    'wallet': DeltaCrownWallet,
    'recent_transactions': List[DeltaCrownTransaction][:5],
    'pending_payouts': List[dict],   # From economy.services.WalletService
    
    # Activity (from UserActivity model)
    'recent_activity': List[UserActivity][:10],
    
    # Notifications
    'unread_count': int,
    
    # Quick Actions
    'profile_completion': int,       # 0-100% (avatar, bio, game IDs, KYC)
    'missing_fields': List[str],     # ["avatar", "bio"] if incomplete
    
    # Audit Metadata
    'last_login': datetime,
    'last_profile_update': datetime,  # From UserAuditEvent.filter(event_type=PROFILE_UPDATED).last()
}
```

#### 3.2.4 Template Structure
```django
{# templates/user_profile/dashboard.html #}
{% extends "base.html" %}

{% block content %}
<div class="dashboard-container grid grid-cols-1 lg:grid-cols-3 gap-6">
    {# Left Column: Quick Stats #}
    <div class="lg:col-span-2">
        {% include "user_profile/components/profile_completion_card.html" %}
        {% include "user_profile/components/recent_activity_card.html" %}
        {% include "user_profile/components/upcoming_matches_card.html" %}
    </div>
    
    {# Right Column: Wallet + Notifications #}
    <div>
        {% include "user_profile/components/wallet_card.html" %}
        {% include "user_profile/components/notifications_card.html" %}
    </div>
</div>
{% endblock %}
```

---

### 3.3 PAGE 3: `/me/settings/` (Unified Settings)
**Purpose:** All-in-one settings page (profile, privacy, game IDs, social links, KYC)

#### 3.3.1 Route
```python
path('me/settings/', views.settings_view, name='settings'),
```

#### 3.3.2 View Signature
```python
@login_required
def settings_view(request: HttpRequest) -> HttpResponse:
    """
    Unified settings page. Handles forms for:
    - Profile info (display_name, bio, avatar, banner)
    - Privacy flags (is_private, show_email, show_socials, etc.)
    - Game profiles (add/edit/delete game IDs)
    - Social links (add/edit/delete)
    - KYC upload
    
    ALL mutations write audit events via AuditService.
    """
```

#### 3.3.3 Context Contract
```python
{
    # Core
    'profile': UserProfile,
    'user': User,
    
    # Forms (Django Forms)
    'profile_form': UserProfileForm,
    'privacy_form': PrivacySettingsForm,
    'game_profiles': List[dict],     # From profile.game_profiles JSON
    'social_links': List[SocialLink],
    
    # KYC Status
    'kyc_status': str,               # 'pending' | 'approved' | 'rejected' | None
    'kyc_documents': List[VerificationDocument],
    
    # Active Section (from query param)
    'active_section': str,           # 'profile' | 'privacy' | 'games' | 'socials' | 'kyc'
    
    # Validation Errors (if form submission failed)
    'errors': dict,
}
```

#### 3.3.4 Template Structure
```django
{# templates/user_profile/settings.html (REFACTORED) #}
{% extends "base.html" %}

{% block content %}
<div class="settings-layout flex">
    {# Sidebar Navigation #}
    <aside class="settings-sidebar w-64">
        {% include "user_profile/settings/sidebar.html" %}
    </aside>
    
    {# Main Content #}
    <main class="settings-main flex-1">
        {% if active_section == 'profile' %}
            {% include "user_profile/settings/section_profile.html" %}
        {% elif active_section == 'privacy' %}
            {% include "user_profile/settings/section_privacy.html" %}
        {% elif active_section == 'games' %}
            {% include "user_profile/settings/section_games.html" %}
        {% elif active_section == 'socials' %}
            {% include "user_profile/settings/section_socials.html" %}
        {% elif active_section == 'kyc' %}
            {% include "user_profile/settings/section_kyc.html" %}
        {% endif %}
    </main>
</div>
{% endblock %}
```

#### 3.3.5 Settings Components (Partials)
```
settings/sidebar.html              Navigation tabs
settings/section_profile.html      Avatar, banner, display_name, bio
settings/section_privacy.html      Privacy flags (checkboxes)
settings/section_games.html        Game profiles table + add/edit modals
settings/section_socials.html      Social links table + add/edit modals
settings/section_kyc.html          KYC upload form + status
```

---

### 3.4 PAGE 4: `/me/economy/` (Wallet + Transactions)
**Purpose:** Full wallet view with transaction history and economy sync status

#### 3.4.1 Route
```python
path('me/economy/', views.economy_view, name='economy'),
```

#### 3.4.2 View Signature
```python
@login_required
def economy_view(request: HttpRequest) -> HttpResponse:
    """
    Display wallet, transactions, economy sync status.
    Uses EconomySyncService.ensure_synced() before display.
    Writes WALLET_VIEWED audit event.
    """
```

#### 3.4.3 Context Contract
```python
{
    # Wallet (from EconomySyncService)
    'wallet': DeltaCrownWallet,
    'profile_cash': Decimal,         # profile.cash (should match wallet.balance)
    'is_synced': bool,               # wallet.balance == profile.cash
    'sync_status': str,              # 'synced' | 'drift_detected' | 'error'
    
    # Transactions (paginated)
    'transactions': Page[DeltaCrownTransaction],  # Default: 25 per page
    'total_transactions': int,
    'filters': dict,                 # 'type', 'date_range', 'amount_range'
    
    # Summary Stats
    'total_deposits': Decimal,
    'total_withdrawals': Decimal,
    'total_earnings': Decimal,       # From tournament wins
    'total_fees': Decimal,
    
    # Pending Actions
    'pending_payouts': List[dict],   # From economy.services
    'pending_refunds': List[dict],
}
```

#### 3.4.4 Template Structure
```django
{# templates/user_profile/economy.html #}
{% extends "base.html" %}

{% block content %}
<div class="economy-container">
    {% include "user_profile/components/wallet_header.html" %}
    {% include "user_profile/components/sync_status_alert.html" %}
    {% include "user_profile/components/transaction_filters.html" %}
    {% include "user_profile/components/transaction_table.html" %}
    {% include "user_profile/components/pagination.html" %}
</div>
{% endblock %}
```

---

### 3.5 PAGE 5: `/me/activity/` (Activity Log)
**Purpose:** Display user's activity log (from UserActivity model)

#### 3.5.1 Route
```python
path('me/activity/', views.activity_view, name='activity'),
```

#### 3.5.2 View Signature
```python
@login_required
def activity_view(request: HttpRequest) -> HttpResponse:
    """
    Display user activity log (login, profile_update, tournament_join, etc).
    Writes ACTIVITY_VIEWED audit event.
    """
```

#### 3.5.3 Context Contract
```python
{
    # Activity Log (paginated)
    'activity_log': Page[UserActivity],  # Default: 50 per page
    'total_activities': int,
    
    # Filters
    'filters': dict,                 # 'event_type', 'date_range'
    'event_types': List[tuple],      # Choices for filter dropdown
    
    # Stats
    'total_logins': int,
    'total_profile_updates': int,
    'total_tournament_joins': int,
    'first_activity': datetime,      # profile.created_at
    'last_activity': datetime,       # UserActivity.objects.filter(user_profile=profile).last().timestamp
}
```

#### 3.5.4 Template Structure
```django
{# templates/user_profile/activity.html #}
{% extends "base.html" %}

{% block content %}
<div class="activity-container">
    {% include "user_profile/components/activity_header.html" %}
    {% include "user_profile/components/activity_filters.html" %}
    {% include "user_profile/components/activity_timeline.html" %}
    {% include "user_profile/components/pagination.html" %}
</div>
{% endblock %}
```

---

### 3.6 PAGE 6: `/me/stats/` (Computed Stats)
**Purpose:** Display computed stats from UserProfileStats model

#### 3.6.1 Route
```python
path('me/stats/', views.stats_view, name='stats'),
```

#### 3.6.2 View Signature
```python
@login_required
def stats_view(request: HttpRequest) -> HttpResponse:
    """
    Display computed stats from UserProfileStats model.
    Uses TournamentStatsService.recompute() if data is stale.
    Writes STATS_VIEWED audit event.
    """
```

#### 3.6.3 Context Contract
```python
{
    # Core Stats (from UserProfileStats model)
    'stats': UserProfileStats,
    
    # Computed Properties
    'win_rate': float,               # stats.win_rate property
    'avg_placement': float,          # stats.avg_placement property
    'rank': str,                     # 'Bronze' | 'Silver' | 'Gold' | 'Platinum' | 'Diamond'
    
    # Tournament Breakdown
    'tournament_stats': List[dict],  # Per-tournament stats
    'game_breakdown': dict,          # Stats per game (Valorant, eFootball, etc)
    
    # Time Series (for charts)
    'monthly_earnings': List[dict],  # [{'month': '2025-01', 'earnings': 1000}, ...]
    'monthly_matches': List[dict],
    
    # Metadata
    'last_recompute': datetime,      # stats.last_updated
    'is_stale': bool,                # now() - last_updated > 24 hours
}
```

#### 3.6.4 Template Structure
```django
{# templates/user_profile/stats.html #}
{% extends "base.html" %}

{% block content %}
<div class="stats-container">
    {% include "user_profile/components/stats_header.html" %}
    {% include "user_profile/components/stats_grid.html" %}
    {% include "user_profile/components/stats_charts.html" %}
    {% include "user_profile/components/tournament_breakdown.html" %}
</div>
{% endblock %}
```

---

## 4. COMPONENT LIBRARY

### 4.1 Reusable Components (Partials)
```
components/hero_banner.html            Avatar + banner + follow button
components/identity_card.html          Display name + bio + metadata
components/stats_panel.html            Stats grid (followers, matches, wins)
components/game_profiles.html          Game IDs table
components/recent_activity.html        Activity timeline (last 5)
components/wallet_preview.html         Balance + currency (compact)
components/wallet_header.html          Full wallet header (balance, currency, actions)
components/wallet_card.html            Dashboard widget (compact)
components/transaction_table.html      Paginated transaction list
components/transaction_filters.html    Filter form (type, date, amount)
components/activity_timeline.html      Activity log (timeline UI)
components/activity_filters.html       Filter form (event_type, date)
components/stats_grid.html             Stats grid (4 columns)
components/stats_charts.html           Charts (monthly earnings, matches)
components/tournament_breakdown.html   Per-tournament stats table
components/pagination.html             Pagination controls
components/profile_completion_card.html  Progress bar + missing fields
components/notifications_card.html     Unread notifications widget
```

### 4.2 Form Components
```
forms/profile_form.html                Avatar, banner, display_name, bio
forms/privacy_form.html                Privacy checkboxes
forms/game_profile_form.html           Add/edit game ID modal
forms/social_link_form.html            Add/edit social link modal
forms/kyc_upload_form.html             KYC document upload
```

### 4.3 Modals
```
modals/follow_list_modal.html          Followers/following list
modals/game_profile_modal.html         Add/edit game profile
modals/social_link_modal.html          Add/edit social link
modals/confirm_delete_modal.html       Confirm delete action
```

---

## 5. DATA CONTRACTS (Services)

### 5.1 Service: `get_visible_profile(user, viewer)`
**File:** `apps/user_profile/services/privacy.py` (NEW)

```python
def get_visible_profile(user: User, viewer: User | AnonymousUser) -> dict:
    """
    Return user profile filtered by privacy settings.
    
    Args:
        user: The user whose profile to display
        viewer: The user viewing the profile (can be AnonymousUser)
    
    Returns:
        dict with filtered fields based on privacy settings
    
    Privacy Rules:
        - If profile.is_private AND viewer != owner → Minimal card
        - If profile.show_email = False AND viewer != owner → email = None
        - If profile.show_socials = False AND viewer != owner → social_links = []
        - If profile.show_real_name = False AND viewer != owner → real_full_name = None
        - Wallet/transactions: Owner-only always
    """
```

### 5.2 Service: `AuditService.write_event()`
**File:** `apps/user_profile/services/audit.py` (EXISTING)

```python
# ALL mutations must call this:
AuditService.write_event(
    user_profile=profile,
    event_type=UserAuditEvent.EventType.PROFILE_UPDATED,  # Or appropriate type
    event_data={'field': 'display_name', 'old_value': 'Old', 'new_value': 'New'},
    ip_address=request.META.get('REMOTE_ADDR'),
    user_agent=request.META.get('HTTP_USER_AGENT'),
)
```

### 5.3 Service: `EconomySyncService.ensure_synced()`
**File:** `apps/user_profile/services/economy_sync.py` (EXISTING)

```python
# Call before displaying wallet:
wallet, profile, is_synced = EconomySyncService.ensure_synced(profile)
if not is_synced:
    # Show warning banner
    messages.warning(request, "Wallet sync detected, balance updated.")
```

### 5.4 Service: `TournamentStatsService.recompute()`
**File:** `apps/user_profile/services/tournament_stats.py` (EXISTING)

```python
# Call before displaying stats (if stale):
stats = profile.stats
if stats.is_stale():
    stats = TournamentStatsService.recompute(profile)
```

---

## 6. TAILWIND LAYOUT RULES

### 6.1 Responsive Breakpoints
```css
/* Tailwind defaults (do NOT change) */
sm: 640px   /* Small tablets */
md: 768px   /* Tablets */
lg: 1024px  /* Desktops */
xl: 1280px  /* Large desktops */
2xl: 1536px /* Extra large */
```

### 6.2 Layout Patterns
**Container:**
```html
<div class="container mx-auto px-4 md:px-6 lg:px-8 max-w-7xl">
    <!-- Content -->
</div>
```

**Grid (2-column):**
```html
<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <div class="lg:col-span-2"><!-- Main --></div>
    <div><!-- Sidebar --></div>
</div>
```

**Card:**
```html
<div class="bg-white dark:bg-slate-800 rounded-lg shadow p-6">
    <h2 class="text-xl font-bold mb-4">Card Title</h2>
    <!-- Content -->
</div>
```

**Button (Primary):**
```html
<button class="bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-4 py-2 rounded-lg transition">
    Action
</button>
```

**Form Input:**
```html
<input type="text" class="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500">
```

---

## 7. JAVASCRIPT PATTERNS

### 7.1 Vanilla JS Fetch (AJAX)
```javascript
// Follow/Unfollow
async function toggleFollow(username) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const response = await fetch(`/api/profile/follow/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ username: username }),
    });
    const data = await response.json();
    if (data.success) {
        // Update UI
        document.querySelector('#follow-btn').textContent = data.is_following ? 'Unfollow' : 'Follow';
    }
}
```

### 7.2 Alpine.js (if used, keep minimal)
```html
<div x-data="{ walletBlurred: true }">
    <button @click="walletBlurred = !walletBlurred">
        Toggle Wallet
    </button>
    <div :class="walletBlurred ? 'blur-sm' : ''">
        ${{ wallet.balance }}
    </div>
</div>
```

### 7.3 Progressive Enhancement Pattern
```html
<!-- SSR: Works without JS -->
<form method="post" action="/me/settings/">
    {% csrf_token %}
    <input name="display_name" value="{{ profile.display_name }}">
    <button type="submit">Save</button>
</form>

<!-- Enhanced: AJAX submit if JS enabled -->
<script>
document.querySelector('form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const response = await fetch(e.target.action, { method: 'POST', body: formData });
    if (response.ok) {
        showToast('Saved!');
    }
});
</script>
```

---

## 8. PRIVACY ENFORCEMENT CHECKLIST

### 8.1 Backend (View Layer)
```python
# BEFORE rendering template:
□ Call get_visible_profile(user, viewer)
□ Check is_own_profile (viewer == owner)
□ Filter social_links based on profile.show_socials
□ Filter email based on profile.show_email
□ Filter real_full_name based on profile.show_real_name
□ Wallet/transactions: Owner-only (always)
□ Audit event: Write PROFILE_VIEWED if authenticated
```

### 8.2 Template Layer
```django
{# ALWAYS check is_own_profile before showing sensitive data #}
{% if is_own_profile or profile.show_email %}
    <p>Email: {{ user.email }}</p>
{% endif %}

{% if is_own_profile %}
    <div class="wallet">
        Balance: ${{ wallet.balance }}
    </div>
{% endif %}
```

### 8.3 JavaScript (AJAX)
```javascript
// ALWAYS include CSRF token
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
fetch('/api/profile/update/', {
    headers: { 'X-CSRFToken': csrfToken },
    // ...
});
```

---

## 9. AUDIT TRAIL CHECKLIST

### 9.1 Events to Log (UserAuditEvent.EventType)
```python
PROFILE_VIEWED      # Public profile accessed
PROFILE_UPDATED     # Any field changed
PROFILE_CREATED     # New profile created (rare, usually via signal)
PRIVACY_UPDATED     # Privacy flags changed
EMAIL_CHANGED       # Email updated (high security)
PASSWORD_CHANGED    # Password updated (high security)
WALLET_TRANSACTION  # Economy change
GAME_ID_ADDED       # Game profile added
GAME_ID_UPDATED     # Game profile edited
GAME_ID_REMOVED     # Game profile deleted
SOCIAL_LINK_ADDED   # Social link added
```

### 9.2 Audit Event Template
```python
# views.py
from apps.user_profile.services.audit import AuditService

def some_view(request):
    profile = request.user.profile
    # ... do something ...
    AuditService.write_event(
        user_profile=profile,
        event_type=UserAuditEvent.EventType.PROFILE_UPDATED,
        event_data={'fields_changed': ['display_name', 'bio']},
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT'),
    )
```

---

## 10. VERIFICATION CRITERIA

### 10.1 Definition of Done (Per Page)
```
□ View calls services, never ORM directly
□ Privacy checked via get_visible_profile()
□ Audit event written for mutations
□ Template split into components (<300 lines)
□ SSR fallback (works without JS)
□ CSRF token in all AJAX requests
□ Tailwind classes used (no inline styles)
□ Responsive (mobile, tablet, desktop)
□ Dark mode support (via Tailwind dark: variants)
□ Manual test: Public profile, owner profile, private profile
□ Manual test: Unauthenticated, authenticated, superuser
```

### 10.2 "No Leaks" Checklist
```
□ No direct ORM queries in views (use services)
□ No user.email in public context (unless show_email=True)
□ No profile.phone unless show_phone=True
□ No social_links unless show_socials=True
□ No wallet/transactions unless is_own_profile=True
□ No game_profiles without privacy check
□ No matches/achievements without privacy check
```

---

## 11. DELIVERABLES (Per Page)

### 11.1 Files to Create (Example: `/profile/<public_id>/`)
```
apps/user_profile/views.py                  # public_profile_view()
apps/user_profile/services/privacy.py       # get_visible_profile()
templates/user_profile/profile.html         # Main template
templates/user_profile/profile_private.html # Minimal card (for is_private=True)
templates/user_profile/components/hero_banner.html
templates/user_profile/components/identity_card.html
templates/user_profile/components/stats_panel.html
templates/user_profile/components/game_profiles.html
templates/user_profile/components/recent_activity.html
static/css/user_profile/profile.css         # Custom CSS (if needed beyond Tailwind)
static/js/user_profile/profile.js           # Follow/share actions (Vanilla JS)
```

### 11.2 Tests to Write (Per Page)
```python
# tests/test_public_profile_view.py
def test_public_profile_authenticated():
    """Authenticated user can see public profile"""
def test_public_profile_unauthenticated():
    """Unauthenticated user can see public profile"""
def test_private_profile_owner():
    """Owner can see own private profile"""
def test_private_profile_other_user():
    """Other user sees minimal card for private profile"""
def test_privacy_enforcement_email():
    """Email hidden if show_email=False"""
def test_privacy_enforcement_socials():
    """Social links hidden if show_socials=False"""
def test_audit_event_written():
    """PROFILE_VIEWED event written"""
```

---

## 12. CONCLUSION

**Target:** 6 production-grade pages with privacy-by-default, audit-aware, service-layer-enforced architecture.

**Constraints:** Django Templates + Tailwind + Vanilla JS (NO frameworks).

**Next Step:** Create UP_FE_03_EXECUTION_BACKLOG_AND_GATES.md (implementation plan with backlog items, priorities, and verification gates).

---

**END OF TARGET UI SPECIFICATION**
