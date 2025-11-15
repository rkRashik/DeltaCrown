# Sprint 1 Quick Reference Guide

## 🚀 Implementation Status

✅ **FE-T-001**: Tournament List Page - **COMPLETE**  
✅ **FE-T-002**: Tournament Detail Page - **COMPLETE**  
✅ **FE-T-003**: Registration CTA States - **COMPLETE**  
⏸️ **FE-T-004**: Registration Wizard - **NOT STARTED**

---

## 📁 File Locations

### Templates
```
templates/tournaments/browse/
  ├── list.html              # Main tournament list page
  ├── _filters.html          # Filter bar (game, status, search)
  ├── _tournament_card.html  # Tournament card component
  ├── _status_pill.html      # Status badge
  └── _empty_state.html      # Empty state

templates/tournaments/detail/
  ├── overview.html          # Main detail page
  ├── _hero.html             # Hero section with banner
  ├── _tabs.html             # Tab navigation (Overview/Rules/Prizes)
  ├── _cta_card.html         # Registration CTA (FE-T-003)
  ├── _info_panel.html       # Info sidebar
  ├── _participants_list.html # Participants preview
  └── _schedule_preview.html # Schedule widget

templates/components/
  └── pagination.html        # Reusable pagination component
```

### Static Assets
```
static/tournaments/css/
  ├── tournament-list.css    # List page styles
  └── tournament-detail.css  # Detail page styles

static/tournaments/js/
  ├── filters.js             # Filter interactions
  └── tournament-detail.js   # Detail page interactions
```

### Backend
```
apps/tournaments/
  ├── views.py               # TournamentListView, TournamentDetailView
  └── urls.py                # URL patterns
```

---

## 🔗 URLs

| URL | View | Template | Purpose |
|-----|------|----------|---------|
| `/tournaments/` | TournamentListView | `browse/list.html` | Tournament discovery page |
| `/tournaments/<slug>/` | TournamentDetailView | `detail/overview.html` | Tournament detail page |
| `/tournaments/<slug>/register/` | (Not implemented) | (FE-T-004) | Registration wizard |

---

## 🎨 Components Used

### Existing Components
- `templates/components/game_badge.html` - Game logo/icon badge
- `templates/components/card.html` - Generic card component
- `templates/components/pagination.html` - Pagination controls

### New Components
- `templates/tournaments/browse/_tournament_card.html` - Tournament card with all info
- `templates/tournaments/browse/_status_pill.html` - Color-coded status badges
- `templates/tournaments/detail/_cta_card.html` - Registration CTA with states

---

## 🧪 Testing Checklist

### Manual Tests

**FE-T-001: Tournament List**
- [ ] Navigate to `/tournaments/`
- [ ] Apply game filter (select a game from dropdown)
- [ ] Click status tabs (Registration Open, Live, Upcoming, Completed)
- [ ] Search for a tournament by name
- [ ] Click pagination (Next/Previous)
- [ ] Verify URL parameters preserved (e.g., `/tournaments/?game=1&status=live&page=2`)
- [ ] Test empty state (search for non-existent tournament)
- [ ] Test on mobile (360px width) - filters collapse, cards stack
- [ ] Check keyboard navigation (Tab, Arrow keys for status tabs)

**FE-T-002: Tournament Detail**
- [ ] Navigate to `/tournaments/<slug>/`
- [ ] Verify hero section loads (banner, name, game badge, status pill)
- [ ] Check key info bar (format, date, prize, slots)
- [ ] Click tabs (Overview, Rules, Prizes, Schedule) - content switches
- [ ] Scroll sidebar - verify sticky behavior on desktop
- [ ] Test on mobile - sidebar moves below content
- [ ] Click organizer info - verify display
- [ ] Check breadcrumbs (Home → Tournaments → [Name])

**FE-T-003: Registration CTA States**
- [ ] Open tournament (status=`registration_open`) - "Register Now" button (orange, enabled)
- [ ] Closed tournament (status=`completed`) - "Registration Closed" (gray, disabled)
- [ ] Full tournament (`current_participants >= max_participants`) - "Tournament Full" (gray, disabled)
- [ ] Unauthenticated user - "Login to Register" (redirects to login)
- [ ] Authenticated & registered user - "Registered" (green checkmark)
- [ ] Verify progress bar color (green → yellow → red as slots fill)
- [ ] Verify entry fee display (or "Free Entry" badge)

---

## 🐛 Known Issues

1. **Participants List**: Shows placeholder avatars (API integration pending)
2. **Registration Status**: Direct database query (needs API call)
3. **Search**: Basic substring match (no full-text search yet)
4. **Real-time Updates**: No live polling (FE-T-008)
5. **Mobile Testing**: Not tested on real devices yet

---

## 📝 Code Patterns

### Template Inheritance
```django
{% extends "base.html" %}
{% load static %}

{% block title %}Page Title{% endblock %}
{% block extra_css %}
<link rel="stylesheet" href="{% static 'tournaments/css/page.css' %}">
{% endblock %}
{% block content %}
  <!-- Page content -->
{% endblock %}
{% block extra_js %}
<script src="{% static 'tournaments/js/page.js' %}"></script>
{% endblock %}
```

### Using Components
```django
{% include "tournaments/browse/_tournament_card.html" with tournament=tournament %}
{% include "components/pagination.html" with page_obj=page_obj %}
```

### Filter Forms
```django
<form method="get" action="">
  <select name="game" onchange="this.form.submit()">
    <option value="">All Games</option>
    {% for game in games %}
      <option value="{{ game.id }}" {% if game.id|stringformat:"s" == current_game %}selected{% endif %}>
        {{ game.name }}
      </option>
    {% endfor %}
  </select>
  <!-- Keep other params -->
  <input type="hidden" name="search" value="{{ current_search }}">
  <input type="hidden" name="status" value="{{ current_status }}">
</form>
```

---

## 🚨 Before Production

- [ ] Integrate with backend APIs (replace direct DB queries)
- [ ] Add HTMX polling for real-time updates
- [ ] Optimize images (lazy loading, compression)
- [ ] Run Lighthouse audit (performance, accessibility, SEO)
- [ ] Test on mobile devices (iOS Safari, Chrome Android)
- [ ] Add E2E tests (Playwright or Cypress)
- [ ] Enable CSRF protection for forms
- [ ] Add rate limiting for search/filter endpoints
- [ ] Configure CDN for static assets
- [ ] Add monitoring (Sentry, LogRocket)

---

## 🔄 Next Task: FE-T-004 (Registration Wizard)

**Files to Create**:
```
templates/tournaments/registration/
  ├── wizard.html            # Main wizard wrapper
  ├── step_team.html         # Team selection (with permissions)
  ├── step_fields.html       # Custom fields
  ├── step_payment.html      # Payment method
  ├── step_confirm.html      # Confirmation
  ├── success.html           # Success page
  ├── error.html             # Error page
  └── _progress_bar.html     # Wizard progress indicator

static/tournaments/js/
  └── registration-wizard.js # Step navigation logic

static/tournaments/css/
  └── registration.css       # Wizard styles
```

**Backend Integration**:
- `POST /api/tournaments/<slug>/register/` (existing)
- `GET /api/teams/user/<user_id>/authorized/` (filter teams by permission)
- `GET /api/tournaments/<slug>/registration-form/` (get custom fields)

**Estimated Time**: 4-6 hours

---

## 📞 Support

**Documentation**:
- [Tournament Backlog](../Backlog/FRONTEND_TOURNAMENT_BACKLOG.md)
- [Tournament Sitemap](../Screens/FRONTEND_TOURNAMENT_SITEMAP.md)
- [File Structure](./FRONTEND_TOURNAMENT_FILE_STRUCTURE.md)
- [Testing Strategy](./FRONTEND_TOURNAMENT_TESTING_STRATEGY.md)

**Backend APIs**:
- `apps/tournaments/api/discovery_views.py` - Tournament discovery
- `apps/tournaments/api/tournament_views.py` - Tournament CRUD
- `apps/tournaments/api/registrations.py` - Registration with team permissions

**Questions?** Reference the planning documents or ask the backend team about API endpoints.

---

**Last Updated**: November 15, 2025  
**Sprint 1 Progress**: 75% (3 of 4 items complete)
