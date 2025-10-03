# Quick Reference: Dynamic Tournament Registration Buttons

## For Frontend Developers

### Adding Dynamic Button to Any Template

**Step 1: Add container with data attribute**
```django
<div 
  class="dc-reg-btn-container" 
  data-tournament-slug="{{ tournament.slug }}"
  data-loading="true"
>
  {# Skeleton loader #}
  <div class="dc-btn-skeleton">
    <div class="dc-skeleton-shimmer"></div>
  </div>
</div>
```

**Step 2: Include JavaScript**
```django
{% block extra_js %}
<script src="{% static 'js/tournament-card-dynamic.js' %}"></script>
{% endblock %}
```

**Step 3: Done!**
The script automatically finds all containers with `data-tournament-slug` and loads buttons.

---

## Button States Reference

| State | Color | Icon | Clickable | Description |
|-------|-------|------|-----------|-------------|
| `register` | Blue gradient | user-plus | ✅ Yes | Open for registration |
| `registered` | Green | check-circle | ❌ No | Already registered |
| `request_approval` | Orange | paper-plane | ✅ Yes | Need captain approval |
| `request_pending` | Yellow | hourglass-half | ❌ No | Approval request sent |
| `closed` | Gray | lock | ❌ No | Registration closed |
| `started` | Gray | flag | ❌ No | Tournament started |
| `full` | Gray | users | ❌ No | Tournament full |
| `no_team` | Red | exclamation-triangle | ❌ No | No team for team event |

---

## API Endpoint

**URL**: `/tournaments/api/{slug}/register/context/`

**Method**: GET

**Response**:
```json
{
  "success": true,
  "context": {
    "tournament_slug": "valorant-weekly",
    "button_state": "register",
    "button_text": "Register Now",
    "message": "Optional help text",
    "is_team_event": false,
    "user_registered": false
  }
}
```

---

## CSS Classes

### Skeleton Loaders
```css
.dc-btn-skeleton          /* Card button skeleton */
.btn-skeleton-large       /* Large button skeleton (48px) */
.btn-skeleton-compact     /* Compact button skeleton (38px) */
.dc-skeleton-shimmer      /* Shimmer animation */
```

### Button States
```css
.dc-btn                   /* Base button */
.dc-btn-registered        /* Registered state (green) */
.dc-btn-approval          /* Approval request (orange) */
.dc-btn-pending           /* Pending state (yellow) */
.dc-btn-disabled          /* Disabled state (gray) */
.dc-btn-warning           /* Warning state (red) */
```

---

## JavaScript API

### Tournament Cards
```javascript
// Auto-loads on DOMContentLoaded
// Finds all: .dc-reg-btn-container[data-tournament-slug]

// Manual trigger
const container = document.querySelector('[data-tournament-slug="slug"]');
window.TournamentCardDynamic.loadRegistrationButton(container, 'slug');
```

### Tournament Detail Pages
```javascript
// Loads 3 button locations: hero, sidebar, mobile
// Automatically finds elements by ID:
// - #hero-registration-btn
// - #sidebar-registration-btn
// - #mobile-registration-btn

// Manual trigger
window.TournamentDetailModern.loadRegistrationButtons('slug', [
  { element: heroEl, variant: 'large' },
  { element: sidebarEl, variant: 'compact' }
]);
```

---

## Common Patterns

### Pattern 1: Tournament Card in Loop
```django
{% for tournament in tournaments %}
  <article class="dc-card" data-tournament-slug="{{ tournament.slug }}">
    <h3>{{ tournament.name }}</h3>
    
    <div class="dc-actions">
      <a href="{{ tournament.url }}" class="dc-btn-secondary">View</a>
      
      <div class="dc-reg-btn-container" data-tournament-slug="{{ tournament.slug }}" data-loading="true">
        <div class="dc-btn-skeleton">
          <div class="dc-skeleton-shimmer"></div>
        </div>
      </div>
    </div>
  </article>
{% endfor %}
```

### Pattern 2: Detail Page Hero
```django
<div id="hero-registration-btn" data-tournament-slug="{{ tournament.slug }}">
  <div class="btn-skeleton-large">
    <div class="skeleton-shimmer"></div>
  </div>
</div>
```

### Pattern 3: Inline Button (Compact)
```django
<div style="display:flex; gap:.5rem;">
  <a href="#" class="btn">View Details</a>
  
  <div 
    class="dc-reg-btn-container" 
    data-tournament-slug="{{ tournament.slug }}"
    data-loading="true"
    style="flex:1;"
  >
    <div class="dc-btn-skeleton">
      <div class="dc-skeleton-shimmer"></div>
    </div>
  </div>
</div>
```

---

## Debugging

### Check if scripts loaded
```javascript
console.log(window.TournamentCardDynamic);    // Should be object
console.log(window.TournamentDetailModern);   // Should be object
```

### Monitor API calls
```javascript
// Open DevTools Network tab, filter by "context"
// Look for: /tournaments/api/{slug}/register/context/
```

### Test button rendering
```javascript
// Get test data
fetch('/tournaments/api/valorant-weekly/register/context/')
  .then(r => r.json())
  .then(data => {
    console.log('API Response:', data);
    const container = document.querySelector('[data-tournament-slug="valorant-weekly"]');
    window.TournamentCardDynamic.renderButton(container, data.context);
  });
```

---

## Customization

### Custom Button Styling
```css
/* Override button colors */
.dc-btn {
  background: your-custom-gradient;
}

.dc-btn-registered {
  background: your-custom-green;
  border-color: your-border-color;
}
```

### Custom Loading Text
```javascript
// Modify skeleton HTML before scripts load
document.querySelectorAll('.dc-btn-skeleton').forEach(skeleton => {
  skeleton.innerHTML = '<span>Loading...</span>';
});
```

### Custom Error Handling
```javascript
// Extend the global object
window.TournamentCardDynamic.renderFallbackButton = function(container, msg) {
  container.innerHTML = `<button class="custom-error">${msg}</button>`;
};
```

---

## Migration Checklist

Replacing old static buttons? Follow this checklist:

- [ ] Find template with static button logic
- [ ] Replace `{% if registered %}...{% else %}...{% endif %}` with container
- [ ] Add `data-tournament-slug` attribute
- [ ] Add skeleton loader HTML
- [ ] Include `tournament-card-dynamic.js` script
- [ ] Remove old button template code
- [ ] Test in browser
- [ ] Check API endpoint returns correct data
- [ ] Verify all button states render correctly

---

## Performance Tips

1. **Batch API Calls**: Cards automatically load in parallel
2. **Cache Control**: Set appropriate cache headers on API endpoint
3. **Lazy Loading**: For long lists, consider IntersectionObserver
4. **Prefetch**: Prefetch API responses on hover (advanced)

Example lazy loading:
```javascript
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const container = entry.target;
      const slug = container.dataset.tournamentSlug;
      window.TournamentCardDynamic.loadRegistrationButton(container, slug);
      observer.unobserve(container);
    }
  });
});

document.querySelectorAll('.dc-reg-btn-container').forEach(el => {
  observer.observe(el);
});
```

---

## Best Practices

✅ **DO**:
- Always include skeleton loader for loading state
- Use semantic HTML (button for disabled, anchor for links)
- Test all 8 button states
- Handle API errors gracefully
- Use data attributes for configuration

❌ **DON'T**:
- Don't mix static and dynamic buttons on same page
- Don't hardcode tournament slugs in JavaScript
- Don't skip skeleton loaders (bad UX)
- Don't forget to include the JS file
- Don't modify global button styles without testing

---

## Support

**Documentation**: See `/docs/MODERN_REGISTRATION_INDEX.md`

**API Reference**: See `/docs/MODERN_REGISTRATION_IMPLEMENTATION.md`

**Testing Guide**: See `/docs/MODERN_REGISTRATION_TESTING.md`

**Issues**: Check browser console for errors, verify API endpoint
