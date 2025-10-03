# 🚀 UI/UX Phase B - Quick Start Guide

**Ready in 5 minutes!** Follow these steps to integrate the new countdown timers and capacity tracking.

---

## Step 1: Collect Static Files (1 minute)

```bash
cd "G:\My Projects\WORK\DeltaCrown"
python manage.py collectstatic --noinput
```

This will copy the new CSS/JS files to your staticfiles directory.

---

## Step 2: Update Tournament Detail Template (2 minutes)

**File**: `templates/tournaments/detail.html`

### A. Add CSS to `<head>` section

Find the `{% block extra_head %}` section (around line 6) and add:

```django
{% block extra_head %}
<link rel="stylesheet" href="{% static 'siteui/css/tournament-detail-neo.css' %}?v=5" />
<link rel="stylesheet" href="{% static 'siteui/css/tournament-detail-pro.css' %}?v=2" />
<!-- ADD THESE TWO LINES -->
<link rel="stylesheet" href="{% static 'siteui/css/countdown-timer.css' %}?v=1" />
<link rel="stylesheet" href="{% static 'siteui/css/capacity-animations.css' %}?v=1" />
{% endblock %}
```

### B. Add JavaScript before `</body>`

Find where scripts are loaded (look for existing `<script>` tags or `{% block extra_js %}`) and add:

```django
{% block extra_js %}
<!-- Existing scripts... -->
<script src="{% static 'js/tournament-detail-modern.js' %}?v=3"></script>
<!-- ADD THESE TWO LINES -->
<script src="{% static 'js/countdown-timer.js' %}?v=1"></script>
<script src="{% static 'js/tournament-state-poller.js' %}?v=2"></script>
{% endblock %}
```

### C. Add Countdown to Quick Facts Sidebar

Find the "Quick Facts" card (around line 140) and add the countdown **before** the `<dl>` tag:

```django
<div class="card">
  <h3 class="h3">Quick Facts</h3>
  
  <!-- ADD THIS COUNTDOWN TIMER -->
  {% if schedule and schedule.start_at %}
    <div class="countdown-timer" 
         data-countdown-type="tournament-start"
         data-target-time="{{ schedule.start_at|date:'c' }}"
         data-tournament-slug="{{ ctx.t.slug }}">
    </div>
  {% endif %}
  
  <dl class="meta compact">
    <!-- Existing Quick Facts... -->
  </dl>
</div>
```

### D. Update Capacity Display

Find the slots/capacity line in Quick Facts (around line 160) and change it to:

**BEFORE**:
```django
<div><dt>Slots</dt><dd>{{ capacity.current_teams }}/{{ capacity.max_teams }}</dd></div>
```

**AFTER**:
```django
<div>
  <dt>Capacity</dt>
  <dd data-tournament-slots data-previous-count="0">
    {{ capacity.current_teams }}/{{ capacity.max_teams }}
  </dd>
</div>
```

That's it for the detail page! Save the file.

---

## Step 3: Update Tournament Hub Template (2 minutes)

**File**: `templates/tournaments/hub.html`

### A. Add CSS to `<head>` section

Find the `{% block extra_head %}` section (around line 6) and add:

```django
{% block extra_head %}
<link rel="stylesheet" href="{% static 'siteui/css/tournaments.css' %}">
<!-- ADD THESE TWO LINES -->
<link rel="stylesheet" href="{% static 'siteui/css/countdown-timer.css' %}?v=1">
<link rel="stylesheet" href="{% static 'siteui/css/capacity-animations.css' %}?v=1">
{% endblock %}
```

### B. Add JavaScript

Find the `{% block extra_js %}` section and add:

```django
{% block extra_js %}
<!-- Existing scripts... -->
<script src="{% static 'js/tournament-card-dynamic.js' %}?v=4"></script>
<!-- ADD THESE TWO LINES -->
<script src="{% static 'js/countdown-timer.js' %}?v=1"></script>
<script src="{% static 'js/tournament-state-poller.js' %}?v=2"></script>
{% endblock %}
```

### C. Add Countdown to Featured Tournament Card

Find the hero card section (around line 60) and add countdown before the CTA buttons:

```django
<div class="hero-card">
  <div class="hc-body">
    <!-- Existing tournament info... -->
    
    <!-- ADD THIS COUNTDOWN TIMER -->
    {% if t.schedule and t.schedule.start_at %}
      <div class="countdown-timer" 
           data-countdown-type="tournament-start"
           data-target-time="{{ t.schedule.start_at|date:'c' }}"
           data-tournament-slug="{{ t.slug }}">
      </div>
    {% endif %}
    
    <div class="hc-cta">
      <!-- Existing buttons... -->
    </div>
  </div>
</div>
```

Save the file.

---

## Step 4: Test It! (2 minutes)

### Start Development Server

```bash
python manage.py runserver
```

### Check These Pages

1. **Tournament Hub**: http://localhost:8000/tournaments/
   - Should see countdown on featured tournament (if start date is in future)

2. **Tournament Detail**: http://localhost:8000/tournaments/{any-tournament-slug}/
   - Should see countdown in Quick Facts sidebar
   - Should see animated capacity bar with color

### What to Look For

✅ **Countdown Timer**:
- Shows time in format: "2 days : 05 hours" or "45 : 30" (min:sec)
- Updates every second
- Changes color when urgent (< 1 hour)

✅ **Capacity Bar**:
- Shows colored progress bar below capacity number
- Green = plenty of slots
- Orange = getting full
- Red = almost/full

### Debug Console

Open browser console (F12) and check for:
```
[CountdownTimer] Found X countdown timer(s)
[TournamentPoller] Starting poller for: {slug}
```

If you see errors, check:
1. Static files collected? `python manage.py collectstatic`
2. Template syntax correct? Check for Django template errors
3. JavaScript loaded? View page source, search for "countdown-timer.js"

---

## Step 5: Create Test Tournament (Optional)

To see the countdown in action, create a tournament with a near-future start time:

```bash
python manage.py shell
```

```python
from apps.tournaments.models import Tournament
from apps.tournaments.models.phase1 import TournamentSchedule
from django.utils import timezone
from datetime import timedelta

# Get a tournament
t = Tournament.objects.first()

# Get or create schedule
schedule, _ = TournamentSchedule.objects.get_or_create(tournament=t)

# Set start time to 1 hour from now
schedule.start_at = timezone.now() + timedelta(hours=1)
schedule.registration_open_at = timezone.now() - timedelta(hours=2)
schedule.registration_close_at = timezone.now() + timedelta(minutes=30)
schedule.save()

print(f"Tournament: {t.title}")
print(f"Starts in: 1 hour")
print(f"Registration closes in: 30 minutes")
```

Now visit that tournament's detail page and you'll see:
- Countdown showing ~30 minutes (to registration close)
- When that expires, countdown switches to tournament start (~1 hour)

---

## 🎉 You're Done!

Your tournament pages now have:
- ⏱️ Real-time countdown timers
- 📊 Animated capacity tracking
- 🔔 Browser notifications (when enabled)
- ✨ Professional, modern UI

---

## Troubleshooting

### Countdown Not Showing

**Problem**: The countdown div exists but is empty

**Solution**:
1. Check the `data-target-time` is in the future (not past)
2. Verify the time format is ISO 8601: use `|date:'c'` filter
3. Check browser console for JavaScript errors
4. Verify `countdown-timer.js` is loaded (view page source)

**Debug**:
```javascript
// In browser console:
window.countdownTimers
// Should show array of countdown objects
```

### Capacity Bar Not Showing

**Problem**: Static capacity text but no animated bar

**Solution**:
1. Verify `data-tournament-slots` attribute is on the element
2. Check that state API endpoint works: visit `/tournaments/api/{slug}/state/`
3. Ensure `tournament-state-poller.js` version is v2 (with enhancements)
4. Check browser console for API errors

**Debug**:
```javascript
// In browser console:
window.tournamentPoller
// Should show poller object

// Manually trigger update:
window.tournamentPoller.poll()
```

### CSS Not Loading

**Problem**: Elements look unstyled

**Solution**:
1. Run `python manage.py collectstatic --noinput`
2. Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)
3. Check browser console Network tab for 404 errors
4. Verify CSS files exist in `staticfiles/` directory

### JavaScript Errors

**Problem**: Console shows "Uncaught ReferenceError" or similar

**Solution**:
1. Check script load order (countdown-timer.js before it's used)
2. Verify no syntax errors in template (unclosed {% %} tags)
3. Check that jQuery/Font Awesome are loaded (if used)
4. Clear browser cache and reload

---

## Need Help?

- **Full Documentation**: `docs/UI_UX_IMPROVEMENTS_PHASE_B.md`
- **Integration Snippets**: Run `python scripts/generate_uiux_snippets.py`
- **Summary**: `docs/UI_UX_PHASE_B_SUMMARY.md`

---

## What's Next?

After confirming everything works:

1. **Test on different browsers** (Chrome, Firefox, Safari)
2. **Test on mobile devices** (responsive design)
3. **Proceed to Phase C**: Mobile enhancements (swipe, touch, etc.)
4. **Deploy to production**: Follow `STAGE_8_DEPLOYMENT_GUIDE.md`

---

**Estimated Time**: 5-10 minutes  
**Difficulty**: Easy (copy-paste integration)  
**Risk**: Low (no breaking changes)  
**Impact**: High (significantly improved UX)

🚀 **Happy coding!**
