# Team Create Wizard - Version 2.0

## 🎯 Overview
Modern 6-step team creation wizard with glassmorphism design, real-time validation, draft auto-save, and live preview. Built with vanilla JavaScript ES6+ and Django 5.2+.

## 📂 File Structure
```
templates/teams/team_create/
├── index.html                 # Main template (~900 lines)
└── README.md                  # This file

static/teams/
├── css/
│   └── team-create-v2.css     # Design system (~2000 lines)
└── js/
    └── team-create-v2.js      # Wizard controller (~1100 lines)
```

## ✨ Features

### 1. **6-Step Wizard Flow**
1. **Identity** - Team name & tag with real-time uniqueness validation
2. **Game Selection** - 9 supported games with visual cards
3. **Region** - Dynamic region selection based on chosen game
4. **Branding** - Logo/banner upload with drag-drop, live preview
5. **Roster** - Optional member invitation system
6. **Review** - Final confirmation with all details preview

### 2. **Real-Time Validation**
- **Team Name**: 3-50 chars, debounced AJAX check for duplicates
- **Team Tag**: 2-8 chars, alphanumeric only, uniqueness validation
- **One-Team-Per-Game**: Automatic enforcement via backend
- **File Uploads**: 5MB max, image format validation
- **Form Fields**: Client-side + server-side validation

### 3. **Draft System**
- Auto-saves every 5 seconds while editing
- Stored in browser localStorage + Django cache (7-day expiry)
- Modal prompt on page load if draft exists
- Clear draft option available
- Persists across sessions

### 4. **Live Preview**
- Sidebar shows real-time updates
- Game card thumbnail
- Logo/banner preview
- Team details summary
- Updates as user types

### 5. **UI/UX Excellence**
- **Design**: Dark esports theme, glassmorphism cards, cyan/purple gradients
- **Animations**: Step transitions, toast notifications, loading states
- **Responsive**: Mobile-first (320px+), tablet (768px+), desktop (1200px+)
- **Accessibility**: ARIA labels, keyboard navigation, focus states
- **Icons**: Font Awesome 6.4.0 integration
- **Typography**: Inter font family from Google Fonts

## 🔧 Technical Stack

### Frontend
- **HTML5**: Semantic structure, data attributes
- **CSS3**: Custom properties, Grid, Flexbox, backdrop-filter
- **JavaScript**: ES6+ classes, Fetch API, async/await, debouncing

### Backend
- **Django 5.2+**: Class-based views, forms, signals
- **Python 3.11+**: Type hints, dataclasses
- **Cache**: Redis/Memcached for draft storage

### Dependencies
- Font Awesome 6.4.0 (CDN)
- Google Fonts - Inter (CDN)
- Django static files system

## 🚀 Setup Instructions

### 1. Ensure URLs are Configured
File: `apps/teams/urls.py`

```python
from .views.create import (
    team_create_view,
    validate_team_name,
    validate_team_tag,
    check_existing_team,
    get_game_regions_api,
    save_draft_api,
    load_draft_api,
    clear_draft_api,
)

urlpatterns = [
    path("create/", team_create_view, name="create"),
    path("api/validate-name/", validate_team_name, name="validate_team_name"),
    path("api/validate-tag/", validate_team_tag, name="validate_team_tag"),
    path("api/game-regions/<str:game_code>/", get_game_regions_api, name="game_regions_api"),
    path("api/check-existing-team/", check_existing_team, name="check_existing_team"),
    path("api/save-draft/", save_draft_api, name="save_draft"),
    path("api/load-draft/", load_draft_api, name="load_draft"),
    path("api/clear-draft/", clear_draft_api, name="clear_draft"),
]
```

### 2. Verify Game Assets
Ensure these files exist in `static/img/game_cards/`:
- `Valorant.jpg`
- `CS2.jpg`
- `Dota2.jpg`
- `MobileLegend.jpg`
- `PUBG.jpeg`
- `FreeFire.jpeg`
- `CallOfDutyMobile.jpg`
- `efootball.jpeg`
- `FC26.jpg`

### 3. Collect Static Files
```bash
python manage.py collectstatic --noinput
```

### 4. Run Migrations
```bash
python manage.py migrate teams
```

### 5. Start Development Server
```bash
python manage.py runserver
```

### 6. Access Team Create
Navigate to: `http://localhost:8000/teams/create/`

## 📋 API Endpoints

### Validation Endpoints
| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/teams/api/validate-name/` | POST | Check team name uniqueness | `{available: bool, message: str}` |
| `/teams/api/validate-tag/` | POST | Check team tag uniqueness | `{available: bool, message: str}` |
| `/teams/api/check-existing-team/` | POST | Check if user has team for game | `{has_team: bool, team_name: str?}` |
| `/teams/api/game-regions/<code>/` | GET | Get regions for game | `{regions: [{id, name, code}]}` |

### Draft Endpoints
| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/teams/api/save-draft/` | POST | Save draft to cache | `{success: bool, saved_at: timestamp}` |
| `/teams/api/load-draft/` | GET | Load draft from cache | `{draft: {...}, saved_at: timestamp}` |
| `/teams/api/clear-draft/` | POST | Delete draft | `{success: bool}` |

### Team Creation
| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/teams/create/` | POST | Create team | Redirect to team dashboard |

## 🎨 Design System

### Color Palette
```css
--primary-cyan: #00d9ff;
--primary-purple: #b24bf3;
--success-green: #10b981;
--warning-yellow: #f59e0b;
--error-red: #ef4444;
--dark-bg: #0a0e1a;
--card-bg: rgba(20, 25, 45, 0.6);
```

### Glassmorphism Effect
```css
backdrop-filter: blur(20px);
background: rgba(20, 25, 45, 0.6);
border: 1px solid rgba(255, 255, 255, 0.1);
box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
```

### Typography
- **Headings**: Inter 700 (bold)
- **Body**: Inter 400 (regular)
- **Labels**: Inter 500 (medium)
- **Base Size**: 16px
- **Scale**: 0.875rem → 1rem → 1.25rem → 1.5rem → 2rem

### Spacing System
- Base unit: 8px
- Scale: 4px, 8px, 12px, 16px, 24px, 32px, 48px, 64px

## 🔐 Security Considerations

### CSRF Protection
- All AJAX POST requests include CSRF token
- Token retrieved from Django cookie
- Applied via `X-CSRFToken` header

### Input Validation
- Client-side: Pattern matching, length checks
- Server-side: Django form validation, model constraints
- SQL Injection: Protected by Django ORM
- XSS: Auto-escaped in Django templates

### File Upload Security
- Max size: 5MB
- Allowed formats: JPEG, PNG, GIF, WebP
- Stored in `MEDIA_ROOT/team_logos/`, `team_banners/`
- Served via Django static/media handlers

## 📊 Browser Support

| Browser | Version | Status |
|---------|---------|--------|
| Chrome | 90+ | ✅ Full support |
| Firefox | 88+ | ✅ Full support |
| Safari | 14+ | ✅ Full support |
| Edge | 90+ | ✅ Full support |
| Mobile Safari | iOS 14+ | ✅ Full support |
| Chrome Mobile | Android 90+ | ✅ Full support |

**Note**: Requires `backdrop-filter` support for glassmorphism. Falls back to solid backgrounds on older browsers.

## 🧪 Testing Checklist

### Functional Tests
- [ ] Team name validation (min/max length, uniqueness)
- [ ] Team tag validation (format, uniqueness)
- [ ] Game selection (card click, one-team-per-game check)
- [ ] Region selection (dynamic loading based on game)
- [ ] Logo upload (drag-drop, file select, preview)
- [ ] Banner upload (drag-drop, file select, preview)
- [ ] Roster invitation (optional, skip functionality)
- [ ] Draft save (auto-save, manual save)
- [ ] Draft restore (modal on page load)
- [ ] Draft clear (button functionality)
- [ ] Step navigation (next/previous buttons)
- [ ] Form submission (final review, POST request)

### UI/UX Tests
- [ ] Progress bar updates on step change
- [ ] Live preview updates in real-time
- [ ] Toast notifications appear/disappear
- [ ] Loading overlay during AJAX calls
- [ ] Error messages display correctly
- [ ] Success messages display correctly
- [ ] Animations run smoothly
- [ ] Responsive design on mobile/tablet/desktop
- [ ] Keyboard navigation works
- [ ] Screen reader accessibility

### Edge Cases
- [ ] Network failure during AJAX call
- [ ] Duplicate team name submission
- [ ] Duplicate team tag submission
- [ ] Invalid file format upload
- [ ] File size exceeds 5MB
- [ ] User already has team for selected game
- [ ] Draft restore with corrupted data
- [ ] Form submission without required fields

## 🐛 Common Issues

### Issue: "CSRF token missing"
**Solution**: Ensure Django middleware includes `'django.middleware.csrf.CsrfViewMiddleware'`

### Issue: "Game regions not loading"
**Solution**: Check `apps/common/game_assets.py` has region data for the game

### Issue: "Draft not auto-saving"
**Solution**: Verify browser supports localStorage, check console for errors

### Issue: "Images not displaying"
**Solution**: Run `python manage.py collectstatic` and check `STATIC_URL` in settings

### Issue: "Glassmorphism not working"
**Solution**: Browser doesn't support `backdrop-filter`. Fallback to solid backgrounds.

## 📈 Future Enhancements

### Planned Features
- [ ] Multi-language support (i18n)
- [ ] Dark/light theme toggle
- [ ] Advanced roster management (roles, positions)
- [ ] Team template system (preset branding)
- [ ] Social media integration (Twitter, Discord)
- [ ] Achievement badges display
- [ ] Team statistics preview
- [ ] Invite via email/SMS
- [ ] Bulk roster import (CSV)
- [ ] A/B testing framework

### Performance Optimizations
- [ ] Lazy load game cards
- [ ] Image optimization (WebP, compression)
- [ ] Service worker for offline draft save
- [ ] CDN for static assets
- [ ] HTTP/2 push for critical CSS/JS

## 📝 Changelog

### Version 2.0.0 (2025-01-19)
**Initial Release**
- ✨ 6-step wizard with modern UI
- ✨ Real-time validation via AJAX
- ✨ Draft auto-save system
- ✨ Live preview sidebar
- ✨ Glassmorphism design system
- ✨ Responsive mobile-first layout
- ✨ Accessibility features (ARIA, keyboard nav)
- ✨ Toast notification system
- ✨ Drag-drop file uploads
- ✨ One-team-per-game enforcement

## 🤝 Contributing

### Code Style
- **JavaScript**: 4-space indent, camelCase, JSDoc comments
- **CSS**: 4-space indent, kebab-case classes, organized by section
- **Python**: PEP 8, type hints, docstrings

### Commit Messages
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation update
- `style:` CSS/UI change
- `refactor:` Code restructure
- `test:` Test addition
- `chore:` Maintenance

## 📄 License
Part of DeltaCrown esports platform. Internal use only.

## 👥 Maintainers
- DeltaCrown Development Team

## 📞 Support
For issues or questions, contact: [Your team support channel]

---

**Last Updated**: 2025-01-19  
**Version**: 2.0.0  
**Status**: Production Ready ✅
