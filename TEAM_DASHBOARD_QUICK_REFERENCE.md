# Team Dashboard & Profile - Quick Reference Guide

## 🚀 Quick Start

### Access Dashboard
```
URL: /teams/<team-slug>/dashboard/
Permission: Captain or Manager only
```

### Access Profile
```
URL: /teams/<team-slug>/
Permission: Public (or members for private teams)
```

---

## 📋 Dashboard Features

### 1. Team Info
- View: Name, tag, game, region, followers, members, posts
- Edit: Click "Edit" button → redirects to manage page
- Stats: Wins, losses, win rate display

### 2. Roster Management
**Reorder Players** (Captain only):
1. Drag player card
2. Drop in new position
3. Auto-saves order

**Remove Player**:
1. Click ❌ on player card
2. Confirm removal
3. Player kicked from team

### 3. Pending Invites
- View all pending invites
- **Resend**: Click "Resend" button
- **Cancel**: Click "Cancel" → confirm

### 4. Settings (Quick Toggles)
- ☑️ Public Profile
- ☑️ Allow Join Requests
- ☑️ Show Statistics
- ☑️ Allow Followers

Auto-saves on toggle.

### 5. Activity Feed
Shows last 20 activities:
- Member joined/left
- Posts published
- Matches completed
- Achievements earned

---

## 👥 Profile Features

### Tabs
1. **Overview**: About, stats, recent posts
2. **Roster**: All team members with roles
3. **Achievements**: Timeline by year
4. **Matches**: Upcoming & recent
5. **Media**: Gallery (placeholder)

### Actions
**Follow Team** (logged-in users):
```javascript
Click "Follow" → Creates follow record → Updates count
```

**Join Request** (eligible users):
```javascript
Click "Request to Join" → Sends request to captain
```

**Share Profile**:
```javascript
Click share icon → Native share OR copy link
```

---

## 🔌 API Endpoints

### Dashboard
```
GET  /teams/<slug>/dashboard/          # View dashboard
POST /teams/<slug>/update-roster-order/ # Save order
POST /teams/<slug>/resend-invite/<id>/  # Resend
```

### Profile
```
GET  /teams/<slug>/                    # View profile
POST /teams/<slug>/follow/             # Follow
POST /teams/<slug>/unfollow/           # Unfollow
POST /teams/<slug>/join/               # Join request
```

---

## 🎨 Customization

### Colors (CSS Variables)
```css
:root {
    --primary: #00ff88;         /* Change primary color */
    --secondary: #8b5cf6;       /* Change secondary color */
    --background: #0a0f1e;      /* Change background */
    --card-bg: rgba(15, 23, 42, 0.9); /* Change card color */
}
```

### Toggle Notifications
```javascript
// In team-dashboard.js or team-profile.js
showNotification('Message', 'type'); // type: success, error, warning, info
```

---

## 🐛 Troubleshooting

### Dashboard Not Loading
1. Check user is captain/manager
2. Verify team slug is correct
3. Check browser console for errors

### Follow Button Not Working
1. Ensure user is logged in
2. Check team `allow_followers` setting
3. Verify CSRF token in request

### Roster Order Not Saving
1. Must be captain (not manager)
2. Check JavaScript console
3. Verify network request succeeds

### Stats Not Showing
1. Check team `show_statistics` setting
2. Verify TeamStats record exists
3. Ensure user has view permission

---

## 📱 Mobile Usage

### Dashboard
- Single column layout
- Swipeable sections
- Touch-friendly buttons
- Simplified header

### Profile
- Horizontal scrollable tabs
- Stacked hero section
- Touch-optimized interactions
- Mobile-friendly grids

---

## 🔒 Permissions

### Dashboard Access
- ✅ Team captain
- ✅ Team managers/co-captains
- ❌ Regular members
- ❌ Non-members

### Profile Access
- ✅ Everyone (if public)
- ✅ Members (if private)
- ❌ Non-members (if private)

### Actions
| Action | Permission |
|--------|------------|
| Reorder roster | Captain only |
| Remove player | Captain only |
| Resend invite | Captain only |
| Toggle settings | Captain only |
| Follow team | Logged-in users |
| Join request | Eligible users |

---

## ⚡ Performance Tips

### Optimize Images
```html
<!-- Use WebP format -->
<img src="logo.webp" alt="Team Logo">

<!-- Lazy load -->
<img loading="lazy" src="banner.jpg">
```

### Cache Static Files
```python
# In settings.py
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
```

### Database Queries
```python
# Already optimized with:
.select_related('profile__user')
.prefetch_related('media')
.order_by('-created_at')
```

---

## 🧪 Testing Commands

### Test Dashboard Access
```python
# In Django shell
from django.contrib.auth import get_user_model
from apps.teams.models import Team, TeamMembership

User = get_user_model()
team = Team.objects.get(slug='my-team')
user = User.objects.get(username='captain')
profile = user.profile

# Check captain
team.captain == profile  # Should be True

# Check dashboard access
is_captain = team.captain_id == profile.id  # True
```

### Test Follow
```bash
curl -X POST http://localhost:8000/teams/my-team/follow/ \
  -H "X-CSRFToken: <token>" \
  -H "Cookie: csrftoken=<token>; sessionid=<session>"
```

---

## 📞 Support

### Common Questions

**Q: Can managers access dashboard?**
A: Yes, managers and co-captains have dashboard access.

**Q: How to change roster order?**
A: Drag and drop player cards (captain only).

**Q: Why can't I see stats?**
A: Check team's `show_statistics` setting.

**Q: How to make team private?**
A: Toggle "Public Profile" in dashboard settings.

---

## 🔄 Update Guide

### Add New Activity Type
1. Add to `TeamActivity.ACTIVITY_TYPE_CHOICES`
2. Update icon mapping in templates
3. Create activity record when event occurs

### Add New Tab
1. Add nav item in `team_profile.html`:
```html
<li class="nav-item" data-tab="newtab">
    <i class="icon-name"></i> New Tab
</li>
```
2. Add tab content:
```html
<div class="tab-content" id="tab-newtab">
    <!-- Content here -->
</div>
```

### Add New Setting Toggle
1. Add field to Team model
2. Add toggle in dashboard template:
```html
<input type="checkbox" class="toggle-input" 
       {% if team.new_setting %}checked{% endif %} 
       onchange="toggleSetting('new_setting', this.checked)">
```

---

## 📚 Resources

### Files to Edit
- **Views**: `apps/teams/views/dashboard.py`
- **Templates**: `templates/teams/team_dashboard.html`, `team_profile.html`
- **Styles**: `static/teams/css/team-dashboard.css`, `team-profile.css`
- **Scripts**: `static/teams/js/team-dashboard.js`, `team-profile.js`
- **URLs**: `apps/teams/urls.py`

### Key Models
- `Team` - Main team model
- `TeamMembership` - Roster entries
- `TeamInvite` - Pending invites
- `TeamStats` - Match statistics
- `TeamAchievement` - Achievements
- `TeamActivity` - Activity feed
- `TeamFollower` - Follower records
- `TeamPost` - Team posts

---

*Last Updated: January 2025*
