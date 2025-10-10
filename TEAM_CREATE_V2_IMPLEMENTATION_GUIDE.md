# 🚀 Team Creation V2 - Implementation Guide

**Quick Start:** Follow these steps to complete the redesign.

---

## ✅ Step 1: Review Current Status

**✓ COMPLETED:**
- Template structure (team_create_v2.html) - 850 lines
- Design specification document
- All sections defined (Team Info, Game, Roster, Media)
- Mobile-first HTML structure
- ARIA accessibility tags
- Help modal system

**🚧 IN PROGRESS:**
- CSS file (partially created, needs completion)
- JavaScript file (not started)

**⏳ PENDING:**
- Backend form updates
- Testing on devices
- Production deployment

---

## 📋 Step 2: Complete CSS File

The CSS file needs these sections (in order):

### A. Root Variables ✅ (Done)
- Color system
- Spacing scale
- Border radius
- Shadows
- Transitions

### B. Base Styles (Need to Add)
```css
/* Captain Card */
.captain-card { ... }
.captain-badge { ... }
.player-card-content { ... }

/* Invite Cards */
.invite-card { ... }
.drag-handle { ... }
.player-info { ... }
.sub-toggle { ... }

/* Media Upload */
.media-upload-card { ... }
.upload-area { ... }
.upload-preview { ... }

/* Optional Sections */
.optional-section { ... }
.optional-toggle { ... }
.optional-content { ... }

/* Preview Column */
.preview-column { ... }
.preview-sticky { ... }
.team-card-preview { ... }
.preview-roster { ... }

/* Mobile Preview Toggle */
.mobile-preview-toggle { ... }

/* Buttons */
.btn { ... }
.btn-primary { ... }
.btn-secondary { ... }
.btn-success { ... }

/* Section Actions */
.section-actions { ... }

/* Responsive Breakpoints */
@media (min-width: 768px) { ... }
@media (min-width: 1024px) { ... }
```

### Quick Command to Create Full CSS:
```powershell
# I'll create the complete CSS in the next response
```

---

## 📋 Step 3: Create JavaScript File

Create `static/teams/js/team-create-v2.js` with:

### A. State Management
```javascript
const TeamCreateApp = {
    state: {
        currentStep: 1,
        selectedGame: null,
        invites: [],
        rosterOrder: [],
        formData: {}
    },
    
    init() {
        this.cacheDOM();
        this.bindEvents();
        this.renderGameCards();
        this.loadDraft(); // Optional: restore from localStorage
    }
};
```

### B. Core Functions Needed
1. **Navigation**
   - `nextStep()`
   - `prevStep()`
   - `goToStep()`
   - `updateProgressBar()`

2. **Game Selection**
   - `renderGameCards()`
   - `selectGame(code)`
   - `updateGameInfo()`
   - `updateRoleDropdowns()`

3. **Roster Management**
   - `addInvite()`
   - `removeInvite(id)`
   - `updateRosterStats()`
   - `initDragDrop()` // Use SortableJS or vanilla
   - `validateUser(identifier)`

4. **Media Handling**
   - `handleLogoUpload()`
   - `handleBannerUpload()`
   - `previewImage(file, target)`
   - `validateImageSize()`

5. **Validation**
   - `debounce(func, wait)` // Utility
   - `validateName()`
   - `validateTag()`
   - `validateForm()`

6. **Live Preview**
   - `updatePreview()`
   - `updatePreviewName()`
   - `updatePreviewRoster()`
   - `updatePreviewSocials()`

7. **Form Submission**
   - `handleSubmit(e)`
   - `prepareFormData()`
   - `showLoading()`

---

## 📋 Step 4: Update Backend

### A. Update forms.py
```python
class TeamCreationForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = [
            'name', 'tag', 'description', 'logo', 'game', 'region',
            'banner_image',  # ADD THIS
            'twitter', 'instagram', 'discord',  # ADD THESE
            'youtube', 'twitch', 'linktree'
        ]
```

### B. Update views/create.py
```python
def team_create_view(request):
    if request.method == 'POST':
        form = TeamCreationForm(request.POST, request.FILES, user=request.user)
        
        if form.is_valid():
            # ... existing team creation ...
            
            # NEW: Process roster order
            roster_order = request.POST.get('roster_order', '[]')
            # Store order somewhere (e.g., TeamMembership.order field)
            
            # NEW: Process invites with sub status
            invites_json = request.POST.get('invites_json', '[]')
            invites = json.loads(invites_json)
            for invite_data in invites:
                # Create TeamInvite with is_sub field
                # ...
```

---

## 📋 Step 5: Testing Checklist

### Manual Testing
- [ ] Load page on mobile (Chrome DevTools)
- [ ] Navigate through all 4 steps
- [ ] Select each game, verify roles update
- [ ] Add/remove invites
- [ ] Upload logo and banner (< 2MB)
- [ ] Fill all fields, submit form
- [ ] Verify team created in database
- [ ] Check team dashboard shows correct data

### Browser Testing
- [ ] Chrome (Desktop + Mobile)
- [ ] Firefox (Desktop + Mobile)
- [ ] Safari (Mac + iOS)
- [ ] Edge (Desktop)

### Accessibility Testing
- [ ] Tab through form (keyboard only)
- [ ] Screen reader (NVDA/JAWS)
- [ ] Color contrast (WCAG AA)
- [ ] Touch targets (min 48px)

### Performance Testing
- [ ] Lighthouse score (Performance > 90)
- [ ] Load time < 2s on 3G
- [ ] No console errors
- [ ] No memory leaks (check DevTools)

---

## 📋 Step 6: Deployment

### Staging
```bash
# 1. Update URL routing
# In apps/teams/urls.py, temporarily:
path("create-v2/", team_create_view_v2, name="create_v2"),

# 2. Deploy to staging
git add .
git commit -m "feat: Team creation v2 - modern esports UI"
git push origin staging

# 3. Test thoroughly
# Visit /teams/create-v2/ on staging

# 4. If all good, update main route
path("create/", team_create_view_v2, name="create"),
```

### Production (Gradual Rollout)
```python
# In views/create.py
def team_create_view(request):
    # Feature flag for gradual rollout
    use_v2 = request.GET.get('v', '1') == '2' or \
             request.user.profile.is_beta_tester or \
             random.random() < 0.1  # 10% of users
    
    if use_v2:
        return render(request, 'teams/team_create_v2.html', context)
    else:
        return render(request, 'teams/team_create.html', context)
```

---

## 🎯 Quick Wins (Low-Hanging Fruit)

If time is limited, prioritize:

### MVP Features (Must Have)
1. ✅ Basic 4-step wizard (done)
2. ✅ All form fields visible (done)
3. ⏳ CSS styling (80% done)
4. ⏳ Game selection working
5. ⏳ Form submission working

### V1.1 Features (Nice to Have)
6. ⏳ AJAX validation
7. ⏳ Live preview updates
8. ⏳ Drag-drop reordering
9. ⏳ Image previews
10. ⏳ Social links

### V1.2 Features (Future)
11. ⏳ Auto-save drafts
12. ⏳ Drag-drop file upload
13. ⏳ Image cropping
14. ⏳ Team templates
15. ⏳ Bulk invite import

---

## 🐛 Common Issues & Solutions

### Issue 1: CSS Not Loading
**Solution:** Check static file path, run `collectstatic`, clear browser cache

### Issue 2: JS Errors on Game Selection
**Solution:** Ensure `window.GAME_CONFIGS` is properly passed from Django

### Issue 3: Image Upload Fails
**Solution:** Check `MEDIA_ROOT`, file permissions, max upload size in settings

### Issue 4: AJAX Validation Not Working
**Solution:** Verify CSRF token, check endpoint URLs, inspect network tab

### Issue 5: Mobile Preview Broken
**Solution:** Test CSS media queries, check viewport meta tag, test on real device

---

## 📞 Need Help?

### If CSS is taking too long:
- Use the old CSS as base, just add new classes
- Focus on mobile-first, desktop can come later
- Use browser DevTools to inspect and adjust live

### If JavaScript is complex:
- Start without drag-drop (can add later)
- Skip AJAX validation initially (use native browser validation)
- Focus on form submission first, polish UX after

### If Backend updates are tricky:
- Keep old form, just add new fields
- Don't change database schema (use existing fields)
- Test with small changes first

---

## 🎉 Success Metrics

After deployment, track:

1. **Completion Rate:** % of users who finish form
2. **Drop-off Points:** Where users abandon
3. **Time to Complete:** Average time (should be < 5 min)
4. **Error Rate:** % of failed submissions
5. **Mobile vs Desktop:** Usage breakdown
6. **User Feedback:** Ratings and comments

---

## 📚 Resources

### Design Inspiration
- Valorant Champions Tour team registration
- PUBG Mobile Esports team creation
- Riot Games account setup flows
- Discord server creation wizard

### Technical References
- MDN Web Docs (HTML/CSS/JS)
- Can I Use (browser compatibility)
- WCAG 2.1 Guidelines (accessibility)
- Lighthouse Docs (performance)

---

**Next Action:** Complete the CSS file, then move to JavaScript.

Let me know when you're ready for the complete CSS code!
