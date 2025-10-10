# 📋 Team Creation V2 - Quick Reference

**Last Updated:** October 10, 2025  
**Status:** Design Phase Complete | Ready for Implementation

---

## 📁 Files Overview

| File | Status | Lines | Purpose |
|------|--------|-------|---------|
| `templates/teams/team_create_v2.html` | ✅ Complete | 850 | Main template |
| `static/teams/css/team-create-v2.css` | ⏳ Partial | ~40% | Styles |
| `static/teams/js/team-create-v2.js` | ❌ Pending | 0 | Interactions |
| `TEAM_CREATE_V2_REDESIGN_REPORT.md` | ✅ Complete | 5000+ | Full spec |
| `TEAM_CREATE_V2_IMPLEMENTATION_GUIDE.md` | ✅ Complete | 2000+ | How-to guide |
| `TEAM_CREATE_V2_SUMMARY.md` | ✅ Complete | 1500+ | Overview |

---

## 🎯 Key Features (New in V2)

### Must-Have ✅
1. Social media links (Twitter, Instagram, Discord, YouTube, Twitch, Linktree)
2. Banner image upload
3. Mobile-first responsive layout (360px minimum)
4. Dark esports theme (`#0B0F14` base)
5. Visual progress indicator (4 steps)
6. All form fields visible and functional

### Nice-to-Have ⏳
7. Drag-and-drop roster reordering
8. AJAX validation with debouncing
9. Live preview updates
10. Role management per game
11. Starter/substitute toggle
12. Contextual help tips
13. Character counters
14. Image file previews
15. Touch-optimized (48px targets)

---

## 📱 Responsive Breakpoints

```css
/* Mobile First (Base) */
@media (max-width: 767px) {
    - Single column
    - Stacked sections
    - Floating preview toggle
    - Full-width buttons
}

/* Tablet */
@media (min-width: 768px) {
    - 2-column layout (60/40)
    - Side preview panel
    - 3-column game grid
}

/* Desktop */
@media (min-width: 1024px) {
    - Max 1400px container
    - Sticky preview
    - 4-column game grid
    - Desktop header
}
```

---

## 🎨 Color Palette

```css
/* Dark Base */
--bg-primary: #0B0F14;
--bg-secondary: #151922;
--bg-tertiary: #1E2530;

/* Accents */
--accent-primary: #6366F1; /* Indigo */
--accent-success: #10B981; /* Green */
--accent-danger: #EF4444;  /* Red */
--accent-warning: #F59E0B; /* Amber */

/* Text */
--text-primary: #F9FAFB;   /* White */
--text-secondary: #D1D5DB; /* Light Gray */
--text-muted: #9CA3AF;     /* Gray */
```

---

## 🧩 Section Structure

```
┌─────────────────────────────┐
│  1. Team Information        │
│  - Name, Tag, Region, Desc  │
├─────────────────────────────┤
│  2. Game Selection          │
│  - Visual game cards        │
├─────────────────────────────┤
│  3. Roster Management       │
│  - Captain (locked)         │
│  - Invite players           │
│  - Role assignment          │
├─────────────────────────────┤
│  4. Media & Branding        │
│  - Logo upload              │
│  - Banner upload            │
│  - Social links (optional)  │
└─────────────────────────────┘
```

---

## ⚙️ JavaScript Functions (Planned)

### Navigation
- `nextStep()` - Validate and advance
- `prevStep()` - Go back
- `goToStep(n)` - Jump to step
- `updateProgress()` - Update progress bar

### Game Selection
- `renderGameCards()` - Populate from GAME_CONFIGS
- `selectGame(code)` - Handle selection
- `updateRoleDropdowns()` - Refresh role options

### Roster Management
- `addInvite()` - Add new invite card
- `removeInvite(id)` - Remove invite
- `updateRosterStats()` - Update counters
- `validateUser(identifier)` - AJAX check

### Validation
- `validateName()` - Debounced AJAX
- `validateTag()` - Debounced AJAX
- `validateForm()` - Pre-submit check

### Preview
- `updatePreview()` - Master update function
- `previewImage(file, target)` - FileReader

### Submission
- `handleSubmit(e)` - Process form
- `prepareFormData()` - Build JSON

---

## 🔧 Backend Changes Needed

### 1. Update Form (apps/teams/forms.py)
```python
class TeamCreationForm(forms.ModelForm):
    class Meta:
        fields = [
            'name', 'tag', 'description', 
            'logo', 'banner_image',  # ← Add banner
            'game', 'region',
            'twitter', 'instagram', 'discord',  # ← Add socials
            'youtube', 'twitch', 'linktree'
        ]
```

### 2. Update View (apps/teams/views/create.py)
```python
def team_create_view(request):
    # Change template
    return render(request, 'teams/team_create_v2.html', context)
    
    # Process roster_order
    roster_order = request.POST.get('roster_order', '[]')
    # ...
```

---

## ✅ Testing Checklist

### Functional
- [ ] All 4 steps accessible
- [ ] Game selection updates roles
- [ ] Add/remove invites works
- [ ] Image uploads (< 2MB)
- [ ] Form submits successfully
- [ ] Team created in database
- [ ] Social links saved

### Responsive
- [ ] Mobile 360px
- [ ] Mobile 375px (iPhone)
- [ ] Mobile 414px (Plus)
- [ ] Tablet 768px
- [ ] Desktop 1024px
- [ ] Desktop 1440px
- [ ] Desktop 1920px

### Browsers
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (Mac/iOS)
- [ ] Edge (latest)

### Accessibility
- [ ] Keyboard navigation
- [ ] Screen reader (NVDA/JAWS)
- [ ] Color contrast (WCAG AA)
- [ ] Touch targets (48px min)
- [ ] Focus indicators visible

### Performance
- [ ] Lighthouse score > 90
- [ ] Load time < 2s (3G)
- [ ] No console errors
- [ ] No memory leaks

---

## 🚀 Deployment Steps

### 1. Staging Test
```bash
# Update URL temporarily
path("create-v2/", team_create_view, name="create_v2")

# Test at /teams/create-v2/
```

### 2. A/B Test (Optional)
```python
# Feature flag in view
use_v2 = request.user.profile.is_beta_tester or \
         random.random() < 0.10  # 10% rollout
```

### 3. Full Rollout
```bash
# Make it default
path("create/", team_create_view, name="create")

# Keep v1 as fallback
path("create-v1/", team_create_view_old, name="create_old")
```

---

## 📊 Success Metrics

### Target KPIs
- **Completion Rate:** > 75% (from ~60%)
- **Drop-off Rate:** < 25% (from ~40%)
- **Time to Complete:** < 5 minutes
- **Mobile Usage:** > 40% (from ~25%)
- **Error Rate:** < 5%

### Monitor
- Google Analytics events
- Form submission success/failure
- Step abandonment rates
- Device type breakdown
- Browser error logs

---

## 🐛 Known Issues (Current Version)

1. **Typo fixed:** `create_team_view` → `team_create_view` ✅
2. **Missing banner field** - Now included
3. **No social links** - Now included
4. **Poor mobile UX** - Redesigned
5. **Weak dark theme** - Professional theme

---

## 📞 Quick Commands

### View Current Page
```bash
http://127.0.0.1:8000/teams/create/
```

### Create CSS File
```bash
# Create empty file
New-Item -Path "static/teams/css/team-create-v2.css" -ItemType File

# Or copy from old as base
Copy-Item "static/teams/css/team-create.css" "static/teams/css/team-create-v2.css"
```

### Create JS File
```bash
New-Item -Path "static/teams/js/team-create-v2.js" -ItemType File
```

### Run Server
```bash
python manage.py runserver
```

### Check for Errors
```bash
python manage.py check
```

---

## 💡 Pro Tips

### CSS
- Start with mobile styles (360px base)
- Use CSS variables for easy theming
- Test on real devices, not just DevTools
- Use `prefers-color-scheme` for system dark mode

### JavaScript
- Use `debounce()` for AJAX validation (500ms)
- Store state in one object, not global vars
- Add error handling for all AJAX calls
- Test with slow 3G network throttling

### Testing
- Clear browser cache between tests
- Test on actual mobile devices
- Use keyboard-only navigation
- Run Lighthouse audits
- Check console for errors

---

## 🎯 Priority Order

If time is limited, implement in this order:

1. **CSS Styling** (4 hours) - Make it look good
2. **Game Selection** (2 hours) - Core UX flow
3. **Form Submission** (2 hours) - Must work
4. **Live Preview** (2 hours) - Nice visual feedback
5. **AJAX Validation** (2 hours) - Better UX
6. **Drag-Drop** (3 hours) - Polish feature
7. **Image Previews** (1 hour) - Nice touch
8. **Social Links** (1 hour) - Add backend field

**MVP:** Items 1-3 (8 hours)
**V1.0:** Items 1-5 (12 hours)
**V1.1:** Items 1-8 (17 hours)

---

## 📚 Reference Documents

### For Design Details
→ `TEAM_CREATE_V2_REDESIGN_REPORT.md`

### For Implementation Steps
→ `TEAM_CREATE_V2_IMPLEMENTATION_GUIDE.md`

### For Overview
→ `TEAM_CREATE_V2_SUMMARY.md`

### This Document
→ `TEAM_CREATE_V2_QUICK_REFERENCE.md`

---

**Ready to proceed?** Let me know what you need next!

Options:
- **A)** Complete CSS file
- **B)** Complete JavaScript file
- **C)** Both CSS + JavaScript
- **D)** Backend update guide
- **E)** Testing instructions

Just say "Continue with Option [X]" and I'll proceed.
