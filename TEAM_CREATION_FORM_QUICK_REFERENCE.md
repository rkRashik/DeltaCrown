# 🎮 Advanced Team Creation Form - Quick Reference

## 🚀 Quick Start

### 1. Install Dependencies
```powershell
pip install djangorestframework
pip install Pillow
```

### 2. Update Settings (`deltacrown/settings.py`)
```python
INSTALLED_APPS = [
    ...
    'rest_framework',
]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100
}
```

### 3. Add View Import
In `apps/teams/views/public.py`, add:
```python
from apps.teams.views.advanced_form import create_team_advanced_view
```

Or update `__init__.py`:
```python
from .advanced_form import create_team_advanced_view
```

### 4. Add URL Pattern
In `apps/teams/urls.py`:
```python
urlpatterns = [
    ...
    path("create/advanced/", create_team_advanced_view, name="create_advanced"),
]
```

### 5. Test
```bash
python manage.py runserver
# Navigate to: http://localhost:8000/teams/create/advanced/
```

---

## 📁 Files Created

### Backend
- `apps/teams/serializers.py` - REST API serializers (NEW)
- `apps/teams/views.py` - API views (NEW)
- `apps/teams/views/advanced_form.py` - Form view (NEW)
- `apps/teams/urls.py` - Updated with API routes

### Frontend
- `templates/teams/create_team_advanced.html` - Main form template
- `static/teams/css/team-creation-form.css` - Form styling
- `static/teams/js/team-creation-form.js` - Interactive logic

### Documentation
- `TASK3_IMPLEMENTATION_COMPLETE.md` - Full documentation
- `setup_task3.ps1` - Automated setup script

---

## 🔌 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/teams/api/games/` | GET | List all game configs |
| `/teams/api/games/<code>/` | GET | Get specific game config |
| `/teams/api/games/<code>/roles/` | GET | Get game roles |
| `/teams/api/create/` | POST | Create team with roster |
| `/teams/api/validate/name/` | POST | Check name availability |
| `/teams/api/validate/tag/` | POST | Check tag availability |
| `/teams/api/validate/ign/` | POST | Validate IGN uniqueness |
| `/teams/api/validate/roster/` | POST | Validate roster composition |

---

## 🎯 Form Features

### Step 1: Game Selection
- ✅ Visual card selector
- ✅ Shows roster requirements
- ✅ Dynamic role loading

### Step 2: Team Info
**Required:**
- Team Name (with availability check)
- Team Tag (with availability check)
- Logo (file upload with preview)
- Region (dropdown)

**Optional:**
- Banner image
- Description/Bio
- Base City
- Founding Year
- Motto
- Social links (Discord, Twitter, Instagram, YouTube, Website)

### Step 3: Roster Management
- ✅ Add players via modal
- ✅ Set roles (game-specific)
- ✅ Designate starters/subs
- ✅ Assign captain (required)
- ✅ Real-time capacity tracking
- ✅ Remove/edit players

### Step 4: Review & Submit
- ✅ Summary of all data
- ✅ Final validation
- ✅ Atomic submission

---

## 🎨 UI Components

### Progress Indicator
4-step wizard with visual progress tracking
- Active step: Glowing border
- Completed: Green checkmark
- Animated transitions

### Game Cards
- Grid layout
- Hover effects
- Selection highlight
- Game icons/logos

### Player Cards
- Captain indicator (crown)
- Role badges
- Starter/sub status
- Remove/promote actions

### Live Preview Panel
- Sticky sidebar (desktop)
- Real-time updates
- Team card mockup
- Roster summary

---

## 🔧 JavaScript API

### Main Class: `TeamCreationForm`

```javascript
// Access globally
window.teamForm

// Key methods
teamForm.goToStep(2)              // Navigate to step
teamForm.selectGame('valorant')   // Select game
teamForm.addPlayer(playerData)    // Add to roster
teamForm.removePlayer(playerId)   // Remove from roster
teamForm.makeCaptain(playerId)    // Set captain
teamForm.updatePreview()          // Refresh preview
teamForm.submitForm()             // Submit to API
```

### Event Hooks (for customization)

```javascript
// Override in template
<script>
document.addEventListener('DOMContentLoaded', () => {
    const form = window.teamForm;
    
    // After game selection
    form.onGameSelected = (gameCode) => {
        console.log('Game selected:', gameCode);
    };
    
    // Before step change
    form.beforeStepChange = (currentStep, nextStep) => {
        // Custom validation
        return true; // or false to prevent
    };
    
    // After player added
    form.onPlayerAdded = (player) => {
        console.log('Player added:', player);
    };
});
</script>
```

---

## 🎭 CSS Customization

### Theme Colors

```css
:root {
    --primary-color: #00ff9d;     /* Neon green */
    --secondary-color: #7b2cbf;   /* Purple */
    --danger-color: #ff006e;      /* Pink */
    --success-color: #06ffa5;     /* Cyan */
}
```

### Custom Game Colors

```css
/* Add game-specific themes */
.game-card[data-game="valorant"] {
    --game-color: #ff4655;
}

.game-card[data-game="dota2"] {
    --game-color: #af1e2d;
}
```

### Mobile Breakpoints

```css
/* Tablet */
@media (max-width: 1200px) {
    .form-wrapper {
        grid-template-columns: 1fr;
    }
}

/* Mobile */
@media (max-width: 768px) {
    .game-selector-grid {
        grid-template-columns: 1fr;
    }
}
```

---

## 🧪 Testing

### Manual Test Checklist

#### Step 1: Game Selection
- [ ] Games load from API
- [ ] Can select a game
- [ ] "Next" button enables after selection
- [ ] Game config loads successfully

#### Step 2: Team Info
- [ ] Required fields marked with *
- [ ] Team name availability checked (wait 500ms after typing)
- [ ] Team tag availability checked
- [ ] Logo upload works
- [ ] Banner upload works
- [ ] File previews appear
- [ ] Optional section expands/collapses
- [ ] Social links accept URLs
- [ ] Character counter works

#### Step 3: Roster
- [ ] "Add Player" opens modal
- [ ] Roles populate from game config
- [ ] Can add player
- [ ] Player card appears
- [ ] Roster counts update
- [ ] Can assign captain
- [ ] Can remove player
- [ ] Validation prevents invalid roster

#### Step 4: Review
- [ ] All data summarized correctly
- [ ] Can go back to edit
- [ ] Submit button works
- [ ] Loading overlay appears
- [ ] Redirects on success
- [ ] Shows errors on failure

### API Testing

```powershell
# Test game configs
curl http://localhost:8000/teams/api/games/

# Test game detail
curl http://localhost:8000/teams/api/games/valorant/

# Test name validation
curl -X POST http://localhost:8000/teams/api/validate/name/ `
  -H "Content-Type: application/json" `
  -d '{"game_code":"valorant","name":"Test Team"}'

# Test team creation (with auth token)
curl -X POST http://localhost:8000/teams/api/create/ `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer YOUR_TOKEN" `
  -d @team_data.json
```

---

## 🐛 Troubleshooting

### Issue: "rest_framework" not found
**Solution:**
```bash
pip install djangorestframework
# Add to INSTALLED_APPS in settings.py
```

### Issue: API returns 404
**Solution:**
- Check `teams/urls.py` includes API patterns
- Verify `HAS_DRF = True` check passes
- Restart Django server

### Issue: CSRF token error
**Solution:**
```javascript
// Ensure CSRF token in form
{% csrf_token %}

// Or add to headers
headers: {
    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
}
```

### Issue: File upload fails
**Solution:**
```python
# Ensure MEDIA settings configured
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# In urls.py (development only)
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

### Issue: Preview not updating
**Solution:**
- Check browser console for JavaScript errors
- Ensure event listeners attached
- Verify `teamForm` object exists globally

### Issue: Modal won't close
**Solution:**
```javascript
// Check modal close handler
document.querySelector('.modal-close').addEventListener('click', () => {
    teamForm.closeModal();
});

// Or click outside modal
document.getElementById('playerModal').addEventListener('click', (e) => {
    if (e.target.id === 'playerModal') {
        teamForm.closeModal();
    }
});
```

---

## 🔗 Integration Examples

### Link from Dashboard

```html
<!-- In dashboard template -->
<a href="{% url 'teams:create_advanced' %}" class="btn btn-primary">
    <i class="fas fa-users-crown"></i>
    Create New Team
</a>
```

### Pass User Context

```python
# In view
def create_team_advanced_view(request):
    return render(request, 'teams/create_team_advanced.html', {
        'user_profile_id': request.user.profile.id,
        'available_games': ['valorant', 'cs2', 'dota2']  # Filter games
    })
```

```javascript
// In JavaScript
const USER_PROFILE_ID = {{ user_profile_id }};

// Use in form
playerData.profile_id = USER_PROFILE_ID;
```

### Custom Success Redirect

```javascript
// In team-creation-form.js, submitForm()
if (response.ok) {
    // Custom redirect
    window.location.href = `/dashboard/?team_created=${result.slug}`;
}
```

---

## 📊 Analytics Events (Optional)

```javascript
// Track form progress
gtag('event', 'form_step_completed', {
    'form_name': 'team_creation',
    'step': currentStep
});

// Track game selection
gtag('event', 'game_selected', {
    'game_code': gameCode
});

// Track submission
gtag('event', 'team_created', {
    'game_code': this.selectedGame,
    'roster_size': this.roster.length
});
```

---

## 🎨 Branding Customization

### Custom Logo Positions

```css
/* Square logos */
.game-icon img {
    object-fit: contain;
}

/* Circular logos */
.game-icon img {
    border-radius: 50%;
}
```

### Custom Fonts

```css
/* In team-creation-form.css */
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&display=swap');

body, .team-creation-container {
    font-family: 'Poppins', sans-serif;
}
```

### Dark/Light Mode Toggle

```css
[data-theme="light"] {
    --dark-bg: #ffffff;
    --card-bg: #f5f5f5;
    --text-primary: #000000;
}
```

---

## 📱 Mobile Enhancements

### Touch Gestures

```javascript
// Add swipe between steps
let touchStart = 0;

formPanel.addEventListener('touchstart', (e) => {
    touchStart = e.touches[0].clientX;
});

formPanel.addEventListener('touchend', (e) => {
    const touchEnd = e.changedTouches[0].clientX;
    const diff = touchStart - touchEnd;
    
    if (Math.abs(diff) > 50) {
        if (diff > 0) {
            teamForm.nextStep(); // Swipe left
        } else {
            teamForm.prevStep(); // Swipe right
        }
    }
});
```

### Native App Integration

```javascript
// Detect if running in app webview
const isNativeApp = window.ReactNativeWebView !== undefined;

if (isNativeApp) {
    // Post messages to native app
    window.ReactNativeWebView.postMessage(JSON.stringify({
        type: 'team_created',
        data: teamData
    }));
}
```

---

## 🚀 Performance Tips

### Lazy Load Images

```javascript
// For game icons
<img src="placeholder.svg" 
     data-src="/static/logos/valorant.svg" 
     class="lazy">

// Lazy load script
document.addEventListener('DOMContentLoaded', () => {
    const lazyImages = document.querySelectorAll('img.lazy');
    
    const imageObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                imageObserver.unobserve(img);
            }
        });
    });
    
    lazyImages.forEach(img => imageObserver.observe(img));
});
```

### Debounce API Calls

```javascript
// Already implemented for name/tag validation
let timeout;
input.addEventListener('input', () => {
    clearTimeout(timeout);
    timeout = setTimeout(() => validateName(), 500);
});
```

### Cache Game Configs

```javascript
// Store in localStorage
localStorage.setItem('game_configs', JSON.stringify(configs));

// Load from cache
const cached = localStorage.getItem('game_configs');
if (cached) {
    this.renderGameSelector(JSON.parse(cached));
}
```

---

## ✅ Production Checklist

- [ ] Django REST Framework installed
- [ ] Settings.py updated
- [ ] Migrations applied
- [ ] Static files collected (`python manage.py collectstatic`)
- [ ] API endpoints tested
- [ ] CSRF protection enabled
- [ ] File upload security configured
- [ ] Error logging setup
- [ ] Rate limiting on API (optional)
- [ ] SSL certificate for production
- [ ] Backup database before deployment

---

## 📞 Support

**Documentation**: `TASK3_IMPLEMENTATION_COMPLETE.md`  
**Code Examples**: See `roster_management_examples.py`  
**API Docs**: Check serializers.py docstrings  
**UI Components**: Inspect template comments

---

**Last Updated**: October 9, 2025  
**Version**: 1.0.0  
**Status**: ✅ Production Ready
