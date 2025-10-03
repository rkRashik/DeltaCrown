# 🚀 UI/UX Quick Integration Guide

**Quick Reference**: How to use Phases B, C & D features in your templates

---

## 📦 Installation (One-time Setup)

### Add to Base Template

```django
{# templates/base.html or templates/tournaments/base_tournaments.html #}

{% load static %}

<!DOCTYPE html>
<html lang="en">
<head>
    {% block extra_head %}
        {# Phase B: Real-time Features #}
        <link rel="stylesheet" href="{% static 'siteui/css/countdown-timer.css' %}">
        <link rel="stylesheet" href="{% static 'siteui/css/capacity-animations.css' %}">
        
        {# Phase C: Mobile Enhancements #}
        <link rel="stylesheet" href="{% static 'siteui/css/mobile-enhancements.css' %}">
        
        {# Phase D: Visual Polish #}
        <link rel="stylesheet" href="{% static 'siteui/css/visual-polish.css' %}">
    {% endblock %}
</head>
<body>
    {% block content %}{% endblock %}
    
    {% block extra_js %}
        {# Phase B: Real-time Features #}
        <script src="{% static 'js/countdown-timer.js' %}"></script>
        <script src="{% static 'js/tournament-state-poller.js' %}"></script>
        
        {# Phase C: Mobile Enhancements #}
        <script src="{% static 'js/mobile-enhancements.js' %}"></script>
        
        {# Phase D: Visual Polish #}
        <script src="{% static 'js/visual-polish.js' %}"></script>
    {% endblock %}
</body>
</html>
```

---

## 🎯 Phase B: Real-time Features

### Countdown Timer

```django
{# Shows countdown until registration closes #}
<div class="countdown-timer" 
     data-countdown-type="registration-close"
     data-target-time="{{ tournament.schedule.registration_close_at|date:'c' }}"
     data-tournament-slug="{{ tournament.slug }}">
</div>

{# 5 countdown types available: #}
data-countdown-type="registration-open"   {# Until registration opens #}
data-countdown-type="registration-close"  {# Until registration closes #}
data-countdown-type="tournament-start"    {# Until tournament starts #}
data-countdown-type="check-in-open"       {# Until check-in opens #}
data-countdown-type="check-in-close"      {# Until check-in closes #}
```

### Capacity Tracking

```django
{# Animated capacity bar #}
<div class="slots-info" 
     data-tournament-slots="{{ tournament.slug }}">
    <div class="capacity-display">
        <span class="capacity-text">
            {{ tournament.capacity.current_teams }}/{{ tournament.capacity.max_teams }} Teams
        </span>
        <div class="capacity-bar">
            <div class="capacity-fill" 
                 style="width: {{ tournament.capacity.percentage }}%;">
            </div>
        </div>
    </div>
</div>
```

---

## 📱 Phase C: Mobile Features

### Mobile Navigation

```html
<!-- Hamburger menu button -->
<button class="mobile-menu-toggle" aria-label="Open menu">
    <div class="hamburger-icon">
        <span></span>
        <span></span>
        <span></span>
        <span></span>
    </div>
</button>

<!-- Overlay (closes menu on click) -->
<div class="mobile-menu-overlay"></div>

<!-- Slide-in menu -->
<div class="mobile-menu">
    <div class="mobile-menu-content">
        <div class="mobile-menu-header">
            <h2>Menu</h2>
            <button class="mobile-menu-close" aria-label="Close">×</button>
        </div>
        <nav>
            <a href="/tournaments/">Tournaments</a>
            <a href="/teams/">Teams</a>
            <a href="/players/">Players</a>
        </nav>
    </div>
</div>
```

### Swipeable Carousel

```html
<div class="swipeable-container" data-swipe-initialized="false">
    <div class="swipeable-track">
        <div class="swipeable-item">
            <img src="banner1.jpg" alt="Banner 1">
        </div>
        <div class="swipeable-item">
            <img src="banner2.jpg" alt="Banner 2">
        </div>
        <div class="swipeable-item">
            <img src="banner3.jpg" alt="Banner 3">
        </div>
    </div>
</div>

<script>
// Auto-initializes, or customize:
new MobileEnhancements.SwipeableCarousel(container, {
    autoplay: true,
    autoplayInterval: 5000,
    showIndicators: true,
    loop: true
});
</script>
```

### Touch Feedback

```html
<!-- Add class for visual touch feedback -->
<button class="btn touch-feedback">Register</button>
<a href="/details/" class="card touch-feedback">View Tournament</a>
```

### Mobile Tables → Cards

```html
<!-- Desktop: Table layout -->
<!-- Mobile: Automatic card transformation -->
<table class="standings-table">
    <thead>
        <tr>
            <th>Team</th>
            <th>Wins</th>
            <th>Losses</th>
            <th>Points</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td data-label="Team">Alpha Squad</td>
            <td data-label="Wins">12</td>
            <td data-label="Losses">3</td>
            <td data-label="Points">36</td>
        </tr>
    </tbody>
</table>

<!-- Transforms to mobile cards automatically! -->
```

---

## ✨ Phase D: Visual Polish

### Loading Skeletons

```html
<!-- Container for skeletons -->
<div id="tournament-list"></div>

<script>
// Show skeletons while loading
const skeletons = VisualPolish.SkeletonManager.show(
    document.getElementById('tournament-list'),
    'tournament-card',  // Type: default, tournament-card, user-profile, list-item
    3                   // Count
);

// Fetch data
fetch('/api/tournaments/')
    .then(res => res.json())
    .then(tournaments => {
        const html = tournaments.map(t => `<div class="card">...</div>`).join('');
        VisualPolish.SkeletonManager.replace(skeletons, html);
    });
</script>
```

### Toast Notifications

```javascript
// Show success message
VisualPolish.Toast.success('Tournament created successfully!');

// Show error
VisualPolish.Toast.error('Failed to register. Please try again.');

// Show warning
VisualPolish.Toast.warning('Registration closes in 10 minutes!');

// Show info
VisualPolish.Toast.info('New tournament starting soon.');

// Custom duration (default: 5000ms)
VisualPolish.Toast.success('Saved!', 3000);

// No auto-dismiss
VisualPolish.Toast.info('Important message', 0);
```

### Micro-animations

```html
<!-- Fade in on load -->
<div class="tournament-card fade-in">...</div>

<!-- Slide up from bottom -->
<div class="tournament-card slide-in-up">...</div>

<!-- Scale in (subtle zoom) -->
<div class="modal-dialog scale-in">...</div>

<!-- Attention getter -->
<button class="btn bounce-subtle">New!</button>

<!-- Error shake -->
<div class="form-group error shake">
    <input type="text" class="shake">
</div>

<!-- Pulse (loading indicator) -->
<div class="status-indicator pulse">Live</div>
```

### Stagger Animations (Lists)

```html
<!-- Fade in with stagger -->
<div class="tournament-grid stagger-fade-in">
    <div class="card">Card 1</div>  <!-- Delay: 0.1s -->
    <div class="card">Card 2</div>  <!-- Delay: 0.2s -->
    <div class="card">Card 3</div>  <!-- Delay: 0.3s -->
</div>

<!-- Slide up with stagger -->
<div class="team-list stagger-slide-up">
    <div class="team-item">Team 1</div>
    <div class="team-item">Team 2</div>
    <div class="team-item">Team 3</div>
</div>

<!-- Auto-triggers when scrolled into view! -->
```

### Image Lazy Loading

```html
<!-- Instead of regular img tag -->
<img data-src="/media/tournaments/banner.jpg"
     data-fallback="/static/images/placeholder.jpg"
     alt="Tournament banner"
     class="image-blur-up">

<!-- Loads when scrolled into view with blur-up effect -->
```

### Tooltips

```html
<!-- Add data-tooltip attribute -->
<button data-tooltip="Click to register for this tournament">Register</button>
<span data-tooltip="Team captain role">👑 Captain</span>

<!-- Tooltip appears automatically on hover -->
```

### Form Validation

```html
<form data-validate method="post">
    {% csrf_token %}
    
    <div class="form-group">
        <label for="email">Email</label>
        <input type="email" 
               id="email" 
               name="email" 
               required 
               minlength="5">
        <!-- Error message appears here automatically -->
    </div>
    
    <div class="form-group">
        <label for="username">Username</label>
        <input type="text" 
               id="username" 
               name="username" 
               required 
               minlength="3">
    </div>
    
    <button type="submit" class="btn">Submit</button>
</form>

<!-- Validates on blur, shows errors with shake animation -->
```

### Progress Bars

```html
<!-- Auto-animates to 75% -->
<div class="progress-bar" data-value="75">
    <div class="progress-bar-fill"></div>
</div>

<!-- Or control with JavaScript -->
<div class="progress-bar" id="upload-progress">
    <div class="progress-bar-fill"></div>
</div>

<script>
const progress = new VisualPolish.ProgressBar(
    document.getElementById('upload-progress')
);

progress.setValue(50);        // Set to 50%
progress.increment(10);       // Add 10%
progress.complete();          // Set to 100%
</script>
```

### Alert Messages

```javascript
// Show inline alert
VisualPolish.AlertManager.success('Changes saved!');
VisualPolish.AlertManager.error('Failed to load data.');
VisualPolish.AlertManager.warning('Session expires in 5 min.');
VisualPolish.AlertManager.info('New feature available!');

// Custom container
const container = document.querySelector('.page-alerts');
VisualPolish.AlertManager.success('Saved!', container, true);
```

### Empty States

```html
<div class="empty-state animated">
    <div class="empty-state-icon">
        <img src="{% static 'images/no-tournaments.svg' %}" 
             alt="No tournaments">
    </div>
    <h3 class="empty-state-title">No tournaments yet</h3>
    <p class="empty-state-description">
        Be the first to create a tournament in your region!
    </p>
    <div class="empty-state-action">
        <a href="{% url 'tournaments:create' %}" class="btn">
            Create Tournament
        </a>
    </div>
</div>
```

### Badges & Tags

```html
<!-- Status badges -->
<span class="badge badge-success">Live</span>
<span class="badge badge-warning">Upcoming</span>
<span class="badge badge-danger">Cancelled</span>

<!-- Notification badge (with pulse) -->
<span class="badge badge-primary badge-pulse">3 New</span>
```

---

## 🎨 Common Patterns

### Tournament Card (Full Example)

```django
<div class="tournament-card fade-in hover-lift touch-feedback">
    {# Lazy-loaded image #}
    <img data-src="{{ tournament.banner.url }}"
         alt="{{ tournament.title }}"
         class="image-blur-up">
    
    <div class="card-content">
        <h3>{{ tournament.title }}</h3>
        
        {# Status badge #}
        <span class="badge badge-success">Live</span>
        
        {# Countdown timer #}
        {% if tournament.schedule.registration_close_at %}
        <div class="countdown-timer"
             data-countdown-type="registration-close"
             data-target-time="{{ tournament.schedule.registration_close_at|date:'c' }}"
             data-tournament-slug="{{ tournament.slug }}">
        </div>
        {% endif %}
        
        {# Capacity bar #}
        <div class="capacity-display" 
             data-tournament-slots="{{ tournament.slug }}">
            <span>{{ tournament.capacity.current_teams }}/{{ tournament.capacity.max_teams }}</span>
            <div class="capacity-bar">
                <div class="capacity-fill" 
                     style="width: {{ tournament.capacity.percentage }}%;"></div>
            </div>
        </div>
        
        {# Action button #}
        <a href="{% url 'tournaments:detail' tournament.slug %}" 
           class="btn touch-feedback"
           data-tooltip="View tournament details">
            View Details
        </a>
    </div>
</div>
```

### Form with Validation

```django
<form method="post" data-validate class="registration-form">
    {% csrf_token %}
    
    <div class="form-group">
        <label for="team_name">Team Name</label>
        <input type="text" 
               id="team_name" 
               name="team_name" 
               required 
               minlength="3"
               maxlength="50">
    </div>
    
    <div class="form-group">
        <label for="email">Email</label>
        <input type="email" 
               id="email" 
               name="email" 
               required>
    </div>
    
    <div class="form-group">
        <label for="players">Number of Players</label>
        <select id="players" name="players" required>
            <option value="">Select...</option>
            <option value="3">3 Players</option>
            <option value="5">5 Players</option>
        </select>
    </div>
    
    <button type="submit" class="btn btn-primary touch-feedback">
        Register Team
    </button>
</form>

<script>
// Success handler
document.querySelector('.registration-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Show loading
    const skeletons = VisualPolish.SkeletonManager.show(
        document.querySelector('.form-container'),
        'default',
        1
    );
    
    try {
        const response = await fetch('/api/register/', {
            method: 'POST',
            body: new FormData(e.target)
        });
        
        if (response.ok) {
            VisualPolish.Toast.success('Registration successful!');
            window.location.href = '/tournaments/';
        } else {
            throw new Error('Registration failed');
        }
    } catch (error) {
        VisualPolish.SkeletonManager.hide(skeletons);
        VisualPolish.Toast.error('Failed to register. Please try again.');
    }
});
</script>
```

---

## 🧪 Testing Your Integration

### 1. Visual Test (Browser)
```bash
python manage.py runserver
# Visit: http://localhost:8000/tournaments/
```

**Check**:
- [ ] Countdown timers update every second
- [ ] Capacity bars show correct percentage
- [ ] Mobile menu works on small screens
- [ ] Cards have hover effects
- [ ] Images lazy load
- [ ] Tooltips appear on hover

### 2. Mobile Test (Device/DevTools)
- [ ] Tap targets are at least 44x44px
- [ ] Swipe gestures work
- [ ] Mobile menu slides in smoothly
- [ ] Forms don't trigger iOS zoom
- [ ] Touch feedback visible

### 3. Accessibility Test (Keyboard)
- [ ] Tab through all interactive elements
- [ ] Focus rings visible
- [ ] Enter/Space activates buttons
- [ ] ESC closes modals/menus

---

## 📚 Documentation

- **Phase B Details**: `docs/UI_UX_IMPROVEMENTS_PHASE_B.md`
- **Phase C Details**: `docs/UI_UX_PHASE_C_MOBILE.md`
- **Phase D Details**: `docs/UI_UX_PHASE_D_POLISH.md`
- **Complete Summary**: `docs/UI_UX_COMPLETE_SUMMARY.md`

---

## 🎯 Quick Reference

### JavaScript APIs

```javascript
// Countdown (auto-init via HTML attributes)
// No manual initialization needed

// Mobile Menu
const menu = new MobileEnhancements.MobileMenu();
menu.open();
menu.close();

// Carousel
new MobileEnhancements.SwipeableCarousel(element, options);

// Skeletons
VisualPolish.SkeletonManager.show(container, type, count);
VisualPolish.SkeletonManager.hide(skeletons);
VisualPolish.SkeletonManager.replace(skeletons, content);

// Toasts
VisualPolish.Toast.success(message, duration);
VisualPolish.Toast.error(message, duration);

// Alerts
VisualPolish.AlertManager.success(message, container);

// Progress
const bar = new VisualPolish.ProgressBar(element);
bar.setValue(50);
bar.increment(10);
```

### CSS Classes

```css
/* Animations */
.fade-in, .slide-in-up, .scale-in
.bounce-subtle, .pulse, .wiggle, .shake

/* Stagger */
.stagger-fade-in, .stagger-slide-up

/* Hover Effects */
.hover-lift, .hover-glow, .hover-brighten

/* Touch */
.touch-feedback, .touch-scale

/* Mobile */
.mobile-menu-toggle, .mobile-menu, .swipeable-container

/* Visual Polish */
.skeleton, .badge, .progress-bar, .tooltip, .empty-state
```

---

## ✅ Checklist

After integration, verify:

- [ ] Static files collected: `python manage.py collectstatic`
- [ ] All CSS files loaded (check browser DevTools)
- [ ] All JS files loaded without errors
- [ ] Countdown timers visible and updating
- [ ] Capacity bars animated
- [ ] Mobile menu works
- [ ] Tooltips appear on hover
- [ ] Forms validate properly
- [ ] Images lazy load
- [ ] Animations smooth (60 FPS)

---

**🎉 That's it! Your DeltaCrown platform now has world-class UI/UX!**
