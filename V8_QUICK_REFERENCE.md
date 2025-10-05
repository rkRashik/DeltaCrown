# Tournament Detail V8 - Quick Reference

## 🚀 Quick Start

### Access the Page
```
URL: /tournaments/t/<tournament-slug>/
Example: /tournaments/t/valorant-winter-championship/
```

### Files Location
```
View:     apps/tournaments/views/detail_v8.py
Template: templates/tournaments/detail_v8.html
CSS:      static/siteui/css/tournaments-detail-v8.css
JS:       static/siteui/js/tournaments-detail-v8.js
```

---

## 📦 Context Data Available in Template

```python
{{ tournament }}              # Tournament object
{{ game_data }}               # {name, icon, logo, card, colors}
{{ user_registration }}       # Registration object or None
{{ user_team }}               # Team object or None
{{ can_register }}            # Boolean
{{ register_url }}            # Registration URL string
{{ capacity_info }}           # {total_slots, filled_slots, available_slots, fill_percentage, is_full}
{{ prize_distribution }}      # List of {position, amount, medal, label}
{{ total_prize_pool }}        # Decimal
{{ timeline_events }}         # List of {title, date, status, icon}
{{ participants }}            # List of teams or players
{{ upcoming_matches }}        # QuerySet (max 5)
{{ recent_matches }}          # QuerySet (max 5)
{{ stats }}                   # {total_participants, total_matches, completed_matches, live_matches}
{{ organizer_info }}          # {name, email, phone, website} or None
{{ rules_data }}              # {general, format, conduct, scoring} or None
{{ media_data }}              # {banner, thumbnail, logo, trailer, stream} or None
{{ now }}                     # Current datetime
{{ participant_count }}       # Integer
```

---

## 🎨 CSS Classes Reference

### Layout
```css
.detail-hero                  /* Hero section */
.detail-container             /* Max-width wrapper */
.detail-layout                /* Main grid (content + sidebar) */
.detail-main                  /* Main content column */
.detail-sidebar               /* Sticky sidebar */
```

### Cards
```css
.content-card                 /* Main content card */
.sidebar-card                 /* Sidebar card */
.card-title                   /* Card heading with icon */
.card-header                  /* Card header (flex) */
.card-body                    /* Card content area */
```

### Hero Components
```css
.hero-banner                  /* Background image */
.hero-overlay                 /* Gradient overlay */
.hero-content                 /* Content wrapper */
.hero-breadcrumb              /* Breadcrumb navigation */
.hero-badges                  /* Status badges container */
.hero-badge                   /* Individual badge */
.status-live                  /* Live badge (red + pulse) */
.status-upcoming              /* Upcoming badge (green) */
.status-completed             /* Completed badge (gold) */
.hero-game-icon               /* Game icon */
.hero-title                   /* Tournament title */
.hero-meta                    /* Meta info grid */
.hero-meta-item               /* Individual meta item */
.hero-actions                 /* Action buttons container */
```

### Prize Distribution
```css
.prize-pool-header            /* Prize pool header */
.prize-pool-amount            /* Total amount (large) */
.prize-pool-label             /* "Total Prize Pool" */
.prize-list                   /* Prize items grid */
.prize-item                   /* Individual prize */
.prize-medal                  /* Medal emoji */
.prize-info                   /* Prize text wrapper */
.prize-position               /* Position label */
.prize-amount                 /* Prize amount */
```

### Timeline
```css
.timeline                     /* Timeline container */
.timeline-item                /* Individual event */
.timeline-dot                 /* Status dot */
.timeline-content             /* Event content */
.timeline-icon                /* Event icon */
.timeline-info                /* Text wrapper */
.timeline-title               /* Event title */
.timeline-date                /* Event date */
```

### Matches
```css
.match-list                   /* Matches container */
.match-card                   /* Individual match */
.match-team                   /* Team section */
.match-team-logo              /* Team logo */
.match-team-name              /* Team name */
.match-vs                     /* Center section */
.match-score                  /* Score display */
.match-time                   /* Time display */
.match-status                 /* Status badge */
```

### Participants
```css
.participants-grid            /* Participants grid */
.participant-card             /* Individual participant */
.participant-avatar           /* Avatar image */
.participant-info             /* Text wrapper */
.participant-name             /* Name text */
.participant-meta             /* Meta info */
```

### Sidebar Components
```css
.sidebar-card-title           /* Sidebar card heading */
.registration-status          /* Registration status card */
.registration-status-icon     /* Status icon */
.registration-status-text     /* Status text */
.capacity-bar                 /* Capacity display */
.capacity-stats               /* Stats row */
.capacity-progress            /* Progress bar container */
.capacity-progress-fill       /* Progress fill */
.capacity-percentage          /* Percentage text */
.info-list                    /* Info items list */
.info-item                    /* Individual info */
.info-icon                    /* Info icon */
.info-content                 /* Info text wrapper */
.info-label                   /* Info label */
.info-value                   /* Info value */
.share-buttons                /* Share buttons grid */
.share-btn                    /* Individual share button */
```

### Utility Classes
```css
.btn                          /* Base button */
.btn-primary                  /* Primary button (gradient) */
.btn-secondary                /* Secondary button (glass) */
.text-primary                 /* Primary color text */
.text-secondary               /* Secondary color text */
.text-muted                   /* Muted text */
.text-accent                  /* Accent color text */
.text-center                  /* Center align */
.mt-2                         /* Margin top 2 */
.skeleton-loading             /* Loading state */
```

---

## 🎯 CSS Variables

### Colors
```css
--primary: #00ff88;
--accent: #ff4655;
--gold: #FFD700;
--silver: #C0C0C0;
--bronze: #CD7F32;
```

### Backgrounds
```css
--bg-primary: #0a0a0f;
--bg-secondary: #121218;
--bg-tertiary: #1a1a24;
--bg-elevated: #22222e;
```

### Glass
```css
--glass-bg: rgba(255, 255, 255, 0.03);
--glass-border: rgba(255, 255, 255, 0.08);
--glass-hover: rgba(255, 255, 255, 0.06);
```

### Text
```css
--text-primary: #ffffff;
--text-secondary: rgba(255, 255, 255, 0.8);
--text-muted: rgba(255, 255, 255, 0.5);
```

### Spacing
```css
--spacing-xs: 0.5rem;
--spacing-sm: 0.75rem;
--spacing-md: 1rem;
--spacing-lg: 2rem;
--spacing-xl: 3rem;
```

### Radius
```css
--radius-sm: 8px;
--radius-md: 12px;
--radius-lg: 16px;
--radius-xl: 20px;
--radius-full: 9999px;
```

### Transitions
```css
--transition-fast: 0.15s ease;
--transition-base: 0.3s ease;
--transition-slow: 0.5s ease;
--transition-spring: 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55);
```

---

## 🔧 JavaScript API

### Public Methods

```javascript
// Show toast notification
TournamentDetailV8.showToast(message, type);
// Types: 'info', 'success', 'error'
// Example: TournamentDetailV8.showToast('Registered!', 'success');

// Animate number counter
TournamentDetailV8.animateNumber(element, targetValue, duration);
// Example: TournamentDetailV8.animateNumber(el, 100000, 2000);

// Format currency (Bangladesh Taka)
TournamentDetailV8.formatCurrency(amount);
// Example: TournamentDetailV8.formatCurrency(50000); // ৳50,000

// Show loading state
TournamentDetailV8.showLoading(element);
// Example: TournamentDetailV8.showLoading(cardElement);

// Hide loading state
TournamentDetailV8.hideLoading(element);
// Example: TournamentDetailV8.hideLoading(cardElement);
```

### Share Functions

```javascript
// Facebook
shareToFacebook();

// Twitter
shareToTwitter();

// WhatsApp
shareToWhatsApp();

// Copy link to clipboard
copyLink();
```

---

## 🛠️ Common Customizations

### Add New Timeline Event

**In view (detail_v8.py):**
```python
timeline_events.append({
    'title': 'Quarter Finals',
    'date': your_date,
    'status': 'upcoming' if your_date > now else 'completed',
    'icon': 'trophy'  # or 'play-circle', 'flag-checkered', etc.
})
```

### Add New CSS Variable

**In CSS file:**
```css
:root {
    --my-color: #ff00ff;
}

.my-element {
    color: var(--my-color);
}
```

### Add New Card Section

**In template:**
```html
<div class="content-card">
    <h2 class="card-title">
        <svg><!-- icon --></svg>
        My Section Title
    </h2>
    <div class="card-body">
        <!-- Your content here -->
    </div>
</div>
```

### Modify Hero Background

**Change opacity:**
```css
.hero-banner {
    opacity: 0.5; /* Default: 0.3 */
}
```

**Change overlay gradient:**
```css
.hero-overlay {
    background: linear-gradient(
        to bottom,
        transparent 0%,
        rgba(10, 10, 15, 0.9) 100%
    );
}
```

### Change Prize Medal Emojis

**In view (detail_v8.py):**
```python
medals = {
    1: '🏆',  # Instead of 🥇
    2: '🥈',
    3: '🥉',
    'other': '🎖️'  # Instead of 🏅
}
```

---

## 🐛 Troubleshooting

### CSS Not Loading
```bash
python manage.py collectstatic --noinput --clear
```

### Template Not Found
Check:
1. File exists: `templates/tournaments/detail_v8.html`
2. URLs updated: `from .views.detail_v8 import tournament_detail_v8`
3. Template dirs in settings: `TEMPLATES[0]['DIRS']`

### JavaScript Not Working
1. Check browser console for errors
2. Verify file loaded: View source → search for "tournaments-detail-v8.js"
3. Clear browser cache
4. Check static files collected

### Missing Data in Template
1. Check view returns data in context
2. Use Django Debug Toolbar to inspect context
3. Add debug print in view: `print(context_dict.keys())`
4. Check model relationships with `select_related`

### Query Performance Issues
1. Enable Django Debug Toolbar
2. Check query count (should be ~3)
3. Verify select_related and prefetch_related used
4. Consider adding caching: `@cache_page(60 * 15)`

---

## 📊 Performance Tips

### Optimize Queries
```python
# Good: Use select_related for ForeignKey
tournament = Tournament.objects.select_related(
    'creator', 'finance', 'schedule'
).get(slug=slug)

# Good: Use prefetch_related for reverse ForeignKey
tournament.registrations.prefetch_related('user', 'team')

# Bad: Will cause N+1 queries
for match in tournament.matches.all():
    print(match.team1.name)  # Query for each match
```

### Add Caching
```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # Cache for 15 minutes
def tournament_detail_v8(request, slug):
    # ... view code
```

### Lazy Load Images
```html
<img src="{{ image.url }}" loading="lazy" alt="...">
```

### Use CDN for Static Files
In production, serve static files from CDN:
```python
# settings.py
STATIC_URL = 'https://cdn.example.com/static/'
```

---

## 🔐 Security Considerations

### XSS Protection
```html
<!-- Safe: Auto-escaped -->
{{ tournament.name }}

<!-- Dangerous: No escaping -->
{{ tournament.description|safe }}

<!-- Use for HTML from CKEditor only -->
```

### CSRF Protection
All forms should include:
```html
{% csrf_token %}
```

### User Data Validation
```python
# Always validate user input
if user_registration and user_registration.status == 'APPROVED':
    # Safe to proceed
```

---

## 📱 Responsive Breakpoints

```css
/* Mobile: 320px - 767px */
@media (max-width: 767px) {
    .detail-layout {
        grid-template-columns: 1fr;
    }
}

/* Tablet: 768px - 1023px */
@media (min-width: 768px) and (max-width: 1023px) {
    /* Tablet styles */
}

/* Desktop: 1024px+ */
@media (min-width: 1024px) {
    .detail-layout {
        grid-template-columns: 1fr 380px;
    }
}
```

---

## ✅ Testing Checklist

### Functionality
- [ ] Page loads without errors
- [ ] All sections render
- [ ] User registration status correct
- [ ] Capacity bar animates
- [ ] Share buttons work
- [ ] Links navigate correctly

### Responsive
- [ ] Desktop (1920px)
- [ ] Laptop (1366px)
- [ ] Tablet (768px)
- [ ] Mobile (375px)

### Accessibility
- [ ] Keyboard navigation
- [ ] Screen reader compatible
- [ ] Focus indicators visible
- [ ] Color contrast WCAG AA

### Performance
- [ ] Page load < 2s on 3G
- [ ] No console errors
- [ ] Images lazy load
- [ ] Animations 60fps

---

## 🎓 Additional Resources

### Django Documentation
- [QuerySet API](https://docs.djangoproject.com/en/4.2/ref/models/querysets/)
- [Templates](https://docs.djangoproject.com/en/4.2/topics/templates/)
- [Static Files](https://docs.djangoproject.com/en/4.2/howto/static-files/)

### CSS Documentation
- [CSS Grid](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Grid_Layout)
- [CSS Variables](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties)
- [Backdrop Filter](https://developer.mozilla.org/en-US/docs/Web/CSS/backdrop-filter)

### JavaScript Documentation
- [Intersection Observer](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API)
- [Clipboard API](https://developer.mozilla.org/en-US/docs/Web/API/Clipboard_API)

---

**Version:** 8.0.0  
**Last Updated:** December 2024  
**Status:** Production Ready
