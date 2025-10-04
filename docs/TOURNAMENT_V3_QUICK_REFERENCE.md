# Tournament V3 Quick Reference Guide

**Quick access guide for developers working with the V3 tournament system**

---

## 🎯 Quick Start

### Enable V3 on a Page

**Detail Page** (already done):
```html
<link href="{% static 'siteui/css/tournaments-v3-detail.css' %}?v=3" />
<script src="{% static 'js/tournaments-v3-detail.js' %}?v=3" defer></script>
```

**Hub Page** (already done):
```html
<link href="{% static 'siteui/css/tournaments-v3-detail.css' %}?v=3" />
<link href="{% static 'siteui/css/tournaments-v3-hub.css' %}?v=3" />
<script src="{% static 'js/tournaments-v3-hub.js' %}?v=3" defer></script>
```

---

## 🌐 API Endpoints

### Teams API
```
GET /tournaments/api/t/<slug>/teams/
```
**Query Params**:
- `page` - Page number (default: 1)
- `search` - Search team name

**Response**:
```json
{
  "teams": [
    {
      "id": 1,
      "name": "Team Alpha",
      "tag": "ALPHA",
      "logo": "/media/teams/alpha.png",
      "status": "confirmed",
      "members": [...],
      "checked_in": true,
      "registered_at": "2025-10-01T10:00:00Z"
    }
  ],
  "page": 1,
  "total_pages": 3,
  "total_count": 25
}
```
**Cache**: 2 minutes

### Matches API
```
GET /tournaments/api/<slug>/matches/
```
**Query Params**:
- `status` - Filter by status (live, upcoming, completed)
- `round` - Filter by round name
- `date` - Filter by date (YYYY-MM-DD)

**Response**:
```json
{
  "matches": [
    {
      "id": 1,
      "match_number": "M1",
      "round": "Finals",
      "team1": {...},
      "team2": {...},
      "score1": 2,
      "score2": 1,
      "status": "completed",
      "start_time": "2025-10-04T15:00:00Z",
      "winner": {...},
      "stream_url": "https://..."
    }
  ],
  "total_count": 16
}
```
**Cache**: 1 minute

### Leaderboard API
```
GET /tournaments/api/t/<slug>/leaderboard/
```
**Response**:
```json
{
  "standings": [
    {
      "rank": 1,
      "team": {...},
      "points": 100,
      "wins": 10,
      "losses": 2,
      "win_rate": 83.33
    }
  ],
  "total_teams": 16,
  "last_updated": "2025-10-04T15:30:00Z"
}
```
**Cache**: 2 minutes

### Registration Status API
```
GET /tournaments/api/t/<slug>/registration-status/
```
**Response**:
```json
{
  "is_registered": true,
  "status": "confirmed",
  "team_name": "Team Alpha",
  "registration_date": "2025-10-01T10:00:00Z",
  "can_register": false,
  "reason": "Already registered"
}
```
**Cache**: None (real-time)

### Featured Tournaments API
```
GET /tournaments/api/featured/
```
**Response**:
```json
{
  "featured": [
    {
      "id": 1,
      "slug": "test-tournament",
      "name": "Test Tournament",
      "game": "valorant",
      "status": "published",
      "banner_image": "/media/...",
      "prize_pool_bdt": 50000,
      "start_at": "2025-10-10T10:00:00Z",
      "is_registration_open": true
    }
  ]
}
```
**Cache**: 5 minutes

---

## 🎨 CSS Classes Reference

### Buttons
```html
<button class="btn btn-primary">Primary</button>
<button class="btn btn-primary-lg">Large Primary</button>
<button class="btn btn-accent">Accent</button>
<button class="btn btn-ghost">Ghost</button>
<button class="btn btn-secondary">Secondary</button>
```

### Cards
```html
<!-- Tournament Card -->
<div class="tournament-card-modern">...</div>

<!-- Team Card -->
<div class="team-card">...</div>

<!-- Match Card -->
<div class="match-card">...</div>
```

### Status Badges
```html
<span class="detail-status-badge live">Live</span>
<span class="detail-status-badge registration">Registration Open</span>
<span class="detail-status-badge upcoming">Upcoming</span>
<span class="detail-status-badge completed">Completed</span>
```

### Loading States
```html
<div class="teams-loading">
  <div class="detail-skeleton detail-skeleton-title"></div>
  <div class="detail-skeleton detail-skeleton-text"></div>
</div>
```

### Empty States
```html
<div class="empty-state">
  <div class="empty-state-icon">🏆</div>
  <h3 class="empty-state-title">No Tournaments Found</h3>
  <p class="empty-state-text">Try adjusting your filters.</p>
</div>
```

---

## 🎮 JavaScript API

### Detail Page Controller

```javascript
// Access global instance
const detail = window.tournamentDetail;

// Manually load data
detail.loadTeams();
detail.loadMatches();
detail.loadLeaderboard();

// Switch tabs programmatically
detail.switchTab('teams');
detail.switchTab('matches');
detail.switchTab('standings');

// Stop real-time updates
detail.stopRealTimeUpdates();

// Start real-time updates
detail.startRealTimeUpdates();
```

### Hub Page Controller

```javascript
// Access global instance
const hub = window.tournamentHub;

// Reset filters
hub.resetFilters();

// Apply specific filter
hub.handleGameFilter('valorant');
hub.handleStatusFilter('live');
hub.handleFeeFilter('free');
hub.handlePrizeFilter('high');

// Search
hub.handleSearchInput('tournament name');

// Load tournaments
hub.loadTournaments(true); // true = reset page

// Carousel controls
hub.nextFeatured();
hub.prevFeatured();
```

---

## 🎨 CSS Variables

### Colors
```css
var(--primary)        /* #00ff88 - Neon green */
var(--accent)         /* #ff4655 - Red */
var(--dark-bg)        /* #0a0e27 - Background */
var(--dark-card)      /* #141b34 - Card background */
var(--text-primary)   /* #ffffff - Main text */
var(--text-secondary) /* #a0aec0 - Secondary text */
var(--text-muted)     /* #718096 - Muted text */
```

### Spacing
```css
var(--space-xs)   /* 4px */
var(--space-sm)   /* 8px */
var(--space-md)   /* 16px */
var(--space-lg)   /* 24px */
var(--space-xl)   /* 32px */
var(--space-2xl)  /* 48px */
var(--space-3xl)  /* 64px */
```

### Typography
```css
var(--text-xs)   /* 12px */
var(--text-sm)   /* 14px */
var(--text-base) /* 16px */
var(--text-lg)   /* 18px */
var(--text-xl)   /* 20px */
var(--text-2xl)  /* 24px */
var(--text-3xl)  /* 30px */
var(--text-4xl)  /* 36px */
var(--text-5xl)  /* 48px */
```

### Transitions
```css
var(--transition-fast) /* 150ms */
var(--transition-base) /* 300ms */
var(--transition-slow) /* 500ms */
```

---

## 🔧 Common Tasks

### Add a New Status Badge Color
```css
.detail-status-badge.custom {
    background: #your-color;
    color: white;
    box-shadow: 0 0 20px rgba(your-color-rgb, 0.3);
}
```

### Create Custom Card
```html
<div class="custom-card">
  <div class="custom-card-header">
    <h3>Title</h3>
  </div>
  <div class="custom-card-body">
    Content here
  </div>
</div>
```

```css
.custom-card {
    background: var(--dark-card);
    border-radius: var(--radius-lg);
    padding: var(--space-xl);
    border: 1px solid rgba(255, 255, 255, 0.05);
    transition: all var(--transition-base);
}

.custom-card:hover {
    transform: translateY(-4px);
    border-color: var(--primary);
    box-shadow: 0 8px 24px rgba(0, 255, 136, 0.15);
}
```

### Add Animation
```css
@keyframes customFade {
    from { opacity: 0; }
    to { opacity: 1; }
}

.custom-element {
    animation: customFade 0.5s ease-out;
}
```

### Override Component Style
```css
/* Specific override */
.custom-page .tournament-card-modern {
    background: var(--your-background);
}

/* Use !important sparingly */
.force-style {
    color: red !important;
}
```

---

## 🐛 Debugging Tips

### Check API Response
```javascript
fetch('/tournaments/api/t/test-slug/teams/')
  .then(r => r.json())
  .then(data => console.log(data));
```

### Check Cache
```python
from django.core.cache import cache
print(cache.get('tournament:teams:1:page:1'))
cache.clear()  # Clear all cache
```

### Check JavaScript Errors
```javascript
// Browser console
window.tournamentDetail  // Should be defined
window.tournamentHub     // Should be defined

// Check event listeners
getEventListeners(document.querySelector('.detail-tab'))
```

### Force CSS Reload
```html
<!-- Add timestamp to force reload -->
<link href="{% static 'siteui/css/tournaments-v3-detail.css' %}?v={{ timestamp }}">
```

---

## 📱 Responsive Breakpoints

```css
/* Mobile (320px - 767px) */
@media (max-width: 767px) {
    /* Mobile styles */
}

/* Tablet (768px - 1023px) */
@media (max-width: 1023px) {
    /* Tablet styles */
}

/* Desktop (1024px+) */
@media (min-width: 1024px) {
    /* Desktop styles */
}
```

---

## ⚡ Performance Tips

### 1. Use Caching
```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # Cache for 5 minutes
def my_view(request):
    ...
```

### 2. Optimize Queries
```python
# Bad
tournaments = Tournament.objects.all()
for t in tournaments:
    print(t.registrations.count())  # N+1 query!

# Good
tournaments = Tournament.objects.annotate(
    reg_count=Count('registrations')
)
for t in tournaments:
    print(t.reg_count)  # Single query!
```

### 3. Lazy Load Images
```html
<img src="{{ image.url }}" loading="lazy" alt="...">
```

### 4. Debounce Events
```javascript
let timer;
input.addEventListener('input', (e) => {
    clearTimeout(timer);
    timer = setTimeout(() => {
        // Your code here
    }, 500);
});
```

---

## 🎯 Keyboard Shortcuts

### Detail Page
- `1` - Teams tab
- `2` - Matches tab
- `3` - Standings tab
- `4` - Prizes tab
- `5` - Rules tab
- `6` - Schedule tab
- `Esc` - Close modals

### Hub Page
- `Ctrl/Cmd + K` - Focus search
- `Esc` - Close filter sidebar

---

## 📞 Need Help?

1. **Check Documentation**: [TOURNAMENT_V3_COMPLETE.md](./TOURNAMENT_V3_COMPLETE.md)
2. **Browser Console**: Check for JavaScript errors
3. **Django Logs**: Check server logs for Python errors
4. **Network Tab**: Check API responses
5. **Contact Team**: Reach out to development team

---

**Last Updated**: October 4, 2025  
**Version**: 3.0.0
