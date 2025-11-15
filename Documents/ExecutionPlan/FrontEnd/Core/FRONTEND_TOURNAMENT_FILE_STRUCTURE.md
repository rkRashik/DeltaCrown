# Frontend Tournament File Structure

**Date**: November 15, 2025  
**Purpose**: Define final template and static folder layout for tournament frontend  
**Status**: Planning Complete

---

## Overview

This document defines the complete folder structure for tournament-related frontend files. All paths are relative to the Django project root.

**Principles**:
- **Modularity**: Each page/feature has dedicated templates and partials
- **Reusability**: Shared components in `templates/components/`
- **Separation**: Templates vs static vs backend logic clearly separated
- **Maintainability**: No "god" templates (max 200 lines per file)
- **DRY**: Use Django template inheritance and includes

---

## Template Structure

### Root Templates

```
templates/
├── base.html                       # Base template with navbar, footer
├── base_no_footer.html             # For full-page experiences (e.g., tournament lobby)
├── components/                     # Reusable components
│   ├── card.html                   # Generic card component
│   ├── game_badge.html             # Game logo/icon badge
│   ├── status_pill.html            # Status indicator (open/closed/live)
│   ├── countdown_timer.html        # Countdown timer component
│   ├── user_avatar.html            # User avatar with fallback
│   ├── modal.html                  # Generic modal wrapper
│   └── pagination.html             # Pagination controls
└── ...
```

### Tournament-Specific Templates

```
templates/tournaments/
├── browse/
│   ├── list.html                   # FE-T-001: Tournament discovery page
│   ├── _filters.html               # Game/status filters
│   ├── _tournament_card.html       # Tournament card component
│   └── _empty_state.html           # No tournaments found
│
├── detail/
│   ├── overview.html               # FE-T-002: Tournament detail (state-based)
│   ├── _hero.html                  # Tournament header/hero section
│   ├── _tabs.html                  # Overview/Rules/Participants/Schedule tabs
│   ├── _info_panel.html            # Info sidebar (details, prizes, rules)
│   ├── _participants_list.html     # Registered participants
│   ├── _schedule_preview.html      # Schedule preview widget
│   └── _cta_card.html              # Registration CTA card
│
├── registration/
│   ├── wizard.html                 # FE-T-003/004: Registration wizard wrapper
│   ├── step_team.html              # Step 1: Team selection (authorized teams only)
│   ├── step_fields.html            # Step 2: Custom fields
│   ├── step_payment.html           # Step 3: Payment (if entry fee)
│   ├── step_confirm.html           # Step 4: Confirmation
│   ├── success.html                # Registration success page
│   ├── error.html                  # Registration error page
│   └── _progress_bar.html          # Wizard progress indicator
│
├── lobby/
│   ├── index.html                  # FE-T-007: Tournament lobby/participant hub
│   ├── _checkin.html               # Check-in widget
│   ├── _roster.html                # Participant roster with check-in status
│   ├── _schedule.html              # Match schedule widget
│   ├── _announcements.html         # Organizer announcements
│   └── _communication.html         # Communication panel (P2)
│
├── brackets/
│   ├── bracket.html                # FE-T-008: Live bracket/schedule view
│   ├── _tree.html                  # Bracket tree visualization (SVG)
│   ├── _schedule_list.html         # List view alternative
│   └── _match_card.html            # Match card in bracket
│
├── groups/
│   ├── standings.html              # FE-T-013: Group standings page
│   ├── _group_tabs.html            # Group A/B/C/D tabs
│   ├── _standings_table.html       # Standings table per group
│   └── _group_matches.html         # Match results per group
│
├── matches/
│   ├── detail.html                 # FE-T-009: Match detail/lobby page
│   ├── _match_header.html          # Match header (teams, time, status)
│   ├── _timeline.html              # Match timeline widget
│   ├── _score_report_modal.html    # FE-T-014: Score submission modal
│   ├── _dispute_modal.html         # FE-T-016: Dispute submission modal
│   └── _lobby_chat.html            # Match lobby chat (P2)
│
├── leaderboard/
│   ├── index.html                  # FE-T-010: Tournament leaderboard
│   ├── _leaderboard_table.html     # Leaderboard table
│   └── _live_badge.html            # "LIVE" indicator
│
├── results/
│   ├── final.html                  # FE-T-018: Final results page
│   ├── _podium.html                # Top 3 podium visualization
│   ├── _certificate_cta.html       # Certificate download button
│   └── _tournament_summary.html    # Tournament stats summary
│
└── organizer/
    ├── dashboard.html              # FE-T-020: Organizer dashboard (hosted tournaments)
    ├── manage_tournament.html      # FE-T-021: Manage specific tournament
    ├── _tournament_status_card.html # Tournament status overview
    ├── _participants_table.html    # Participant management table
    ├── _payments_table.html        # Payment tracking table
    ├── _match_controls.html        # Match control actions (reschedule, override)
    │
    ├── groups/
    │   ├── config.html             # FE-T-011: Group configuration interface
    │   ├── draw.html               # FE-T-012: Live group draw interface
    │   ├── _config_form.html       # Group configuration form
    │   ├── _draw_controls.html     # Draw controls (Next, Auto-Assign, Reset)
    │   └── _group_preview.html     # Visual preview of groups
    │
    └── disputes/
        ├── list.html               # Dispute list (if multiple)
        ├── detail.html             # FE-T-017: Dispute resolution page
        ├── _evidence_viewer.html   # Evidence (screenshots, videos)
        └── _resolution_form.html   # Resolution action form
```

### Integration with Existing Templates

**Inherit from**:
- `base.html` for standard pages (navbar + footer)
- `base_no_footer.html` for immersive pages (lobby, live bracket)

**Reuse components from**:
- `templates/components/` (card, game_badge, status_pill, countdown_timer, user_avatar, modal, pagination)
- `templates/partials/navbar.html` (existing navbar)
- `templates/partials/footer.html` (existing footer)

**Dashboard integration**:
- Add tournament widget to `templates/dashboard/index.html` (FE-T-005)
- Widget includes: "My Tournaments" card with upcoming/live tournament summary
- Link to `/dashboard/tournaments/` (P2 full page)

---

## Static Structure

### CSS

```
static/tournaments/
├── css/
│   ├── tournament-list.css         # FE-T-001: Discovery page styles
│   ├── tournament-detail.css       # FE-T-002: Detail page styles
│   ├── registration.css            # FE-T-003/004: Registration wizard
│   ├── lobby.css                   # FE-T-007: Tournament lobby
│   ├── bracket.css                 # FE-T-008: Bracket visualization
│   ├── match-detail.css            # FE-T-009: Match detail page
│   ├── leaderboard.css             # FE-T-010: Leaderboard styles
│   ├── groups.css                  # FE-T-013: Group standings
│   ├── organizer.css               # FE-T-020/021: Organizer dashboard
│   └── shared.css                  # Shared tournament styles (cards, pills, badges)
```

### JavaScript

```
static/tournaments/
├── js/
│   ├── registration-wizard.js      # FE-T-003/004: Multi-step form logic, team selection
│   ├── bracket-renderer.js         # FE-T-008: SVG bracket tree generation
│   ├── live-updates.js             # WebSocket + HTMX integration for real-time updates
│   ├── group-draw.js               # FE-T-012: Live group draw animation
│   ├── match-timeline.js           # FE-T-009: Match timeline rendering
│   ├── score-submission.js         # FE-T-014: Score submission modal logic
│   ├── dispute-form.js             # FE-T-016: Dispute submission form
│   └── filters.js                  # FE-T-001: Discovery page filters (reuse existing filter-orb.js)
```

### Images/Icons

```
static/tournaments/
├── img/
│   ├── tournament-placeholder.png  # Default tournament banner
│   ├── podium-gold.svg            # 1st place podium icon
│   ├── podium-silver.svg          # 2nd place podium icon
│   ├── podium-bronze.svg          # 3rd place podium icon
│   ├── bracket-bg.png             # Bracket background texture
│   └── empty-state.svg            # Empty state illustration
```

### Existing Static Reuse

**From `static/` (existing)**:
- `static/css/components/cards.css` (base card styles)
- `static/css/components/buttons.css` (button styles)
- `static/css/components/forms.css` (form input styles)
- `static/js/countdown-timer.js` (countdown timer logic, used in lobby)
- `static/js/htmx-extensions.js` (HTMX custom extensions)
- `static/siteui/` (orbs, animations, theme variables)

---

## Naming Conventions

### Templates

- **Page templates**: `<page_name>.html` (e.g., `list.html`, `overview.html`, `wizard.html`)
- **Partials/components**: `_<component_name>.html` (e.g., `_filters.html`, `_hero.html`)
- **Modals**: `_<modal_name>_modal.html` (e.g., `_score_report_modal.html`)
- **State-based templates**: Use single template with Django conditionals (`{% if tournament.is_live %}`)

### CSS

- **Lowercase, hyphenated**: `tournament-list.css`, `registration.css`
- **Shared styles**: `shared.css` for cross-page tournament styles
- **Component-specific**: Match template names (e.g., `lobby.css` for `lobby/index.html`)

### JavaScript

- **Lowercase, hyphenated**: `registration-wizard.js`, `bracket-renderer.js`
- **Descriptive names**: Indicate functionality (e.g., `live-updates.js`, `score-submission.js`)
- **No jQuery**: Use vanilla JS or Alpine.js (existing pattern)

---

## File Size Guidelines

### Templates

- **Max 200 lines per file**: Break into partials if exceeding
- **Partials**: Use `{% include %}` for reusable sections
- **Avoid "god" templates**: Split large pages into logical partials

### CSS

- **Max 500 lines per file**: Split into multiple files if needed
- **Use BEM naming**: Block-Element-Modifier pattern (e.g., `.tournament-card__title`)
- **Mobile-first**: Write base styles first, then desktop overrides

### JavaScript

- **Max 300 lines per file**: Split into modules if exceeding
- **ES6 modules**: Use `import`/`export` where possible
- **Event delegation**: Attach listeners to parent elements to reduce memory footprint

---

## Integration Checklist

### Before Implementation

- [ ] **Templates folder**: Verify `templates/tournaments/` exists (create if not)
- [ ] **Static folder**: Verify `static/tournaments/` exists (create if not)
- [ ] **Base templates**: Confirm `base.html` and `base_no_footer.html` support tournament needs
- [ ] **Components**: Audit `templates/components/` for reusable items (card, badge, modal, etc.)
- [ ] **Static dependencies**: Ensure HTMX, Alpine.js, and countdown-timer.js are loaded globally

### During Implementation

- [ ] **Django URLs**: Add URL patterns in `apps/tournaments/urls.py`
- [ ] **Views**: Create views in `apps/tournaments/views.py` (or CBVs)
- [ ] **Template tags**: Create custom template tags/filters if needed (e.g., `{% tournament_status %}`)
- [ ] **Static collection**: Run `python manage.py collectstatic` after adding new CSS/JS
- [ ] **HTMX integration**: Use HTMX for real-time updates (polling, WebSocket fallback)
- [ ] **Mobile testing**: Test all pages on 360px width (mobile-first)

### After Implementation

- [ ] **Linting**: Run template linter (djlint) and CSS/JS linters
- [ ] **Performance**: Check page load times, optimize images
- [ ] **Accessibility**: Verify keyboard navigation, screen reader compatibility
- [ ] **Documentation**: Update SITEMAP if URLs or content change

---

## Example: Tournament Lobby File Organization

### Template: `templates/tournaments/lobby/index.html`

```django
{% extends "base_no_footer.html" %}
{% load static %}

{% block title %}{{ tournament.name }} - Lobby{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{% static 'tournaments/css/lobby.css' %}">
{% endblock %}

{% block content %}
<div class="tournament-lobby">
  <div class="lobby-header">
    {% include "tournaments/lobby/_hero.html" with tournament=tournament %}
  </div>
  
  <div class="lobby-panels">
    {% include "tournaments/lobby/_checkin.html" %}
    {% include "tournaments/lobby/_roster.html" %}
    {% include "tournaments/lobby/_schedule.html" %}
    {% include "tournaments/lobby/_announcements.html" %}
  </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/countdown-timer.js' %}"></script>
<script src="{% static 'tournaments/js/live-updates.js' %}"></script>
{% endblock %}
```

### CSS: `static/tournaments/css/lobby.css`

```css
/* Tournament Lobby Styles */
.tournament-lobby {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.lobby-header {
  margin-bottom: 2rem;
}

.lobby-panels {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
}

@media (max-width: 768px) {
  .lobby-panels {
    grid-template-columns: 1fr;
  }
}
```

### JavaScript: `static/tournaments/js/live-updates.js`

```javascript
// Real-time updates using HTMX polling
document.addEventListener('DOMContentLoaded', function() {
  // HTMX automatically polls roster every 30s via hx-trigger="every 30s"
  // This script handles custom logic if needed
  
  // Example: Flash animation when roster updates
  document.body.addEventListener('htmx:afterSwap', function(evt) {
    if (evt.detail.target.id === 'roster-list') {
      evt.detail.target.classList.add('flash-update');
      setTimeout(() => evt.detail.target.classList.remove('flash-update'), 500);
    }
  });
});
```

---

## Migration Notes

### Existing Templates to Update

**`templates/spectator/tournament_list.html`** → Rename/move to `templates/tournaments/browse/list.html`
- Enhance with better filters
- Add empty state
- Integrate with new CSS

**`templates/tournaments/` (if exists)** → Audit and reorganize
- Merge existing templates into new structure
- Deprecate old paths

### Backward Compatibility

- **Old URLs**: Keep redirects if existing URLs change (e.g., 301 redirect from old `/tournament/<slug>/` to `/tournaments/<slug>/`)
- **Template inheritance**: Ensure old templates still work during migration
- **Static paths**: Use `{% static %}` tag to avoid hardcoded paths

---

## Next Steps

1. **Create folder structure**: Run script to create all folders
2. **Implement FE-T-001** (Tournament List): Start with discovery page as foundation
3. **Create partials**: Build reusable components (`_tournament_card.html`, `_filters.html`)
4. **Test base layout**: Verify `base.html` integration and navbar paths
5. **Iterate**: Complete pages in order of FRONTEND_TOURNAMENT_CHECKLIST.md

---

**Related Documents**:
- [Tournament Backlog](../Backlog/FRONTEND_TOURNAMENT_BACKLOG.md) - Feature specifications
- [Tournament Sitemap](../Screens/FRONTEND_TOURNAMENT_SITEMAP.md) - URL structure
- [Tournament Trace](FRONTEND_TOURNAMENT_TRACE.yml) - Traceability map
- [Implementation Checklist](FRONTEND_TOURNAMENT_CHECKLIST.md) - Task tracking
