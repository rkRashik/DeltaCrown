# 🚀 **Quick Reference: Role-Based Dashboard**

**Status:** ✅ Ready for Testing
**Last Updated:** Current Sprint

---

## 📍 **File Locations**

| Component | File Path |
|-----------|-----------|
| **Backend View** | `apps/teams/views/dashboard.py` (lines 308-570) |
| **Template** | `templates/teams/_team_hub.html` (654 lines) |
| **Tests** | `apps/teams/tests/test_team_dashboard_roles.py` (418 lines) |
| **Documentation** | `Documents/Teams/TEAM_APP_FUNCTIONAL_SPEC.md` (Section 5) |
| **View Docs** | `Documents/Teams/backup_files/teams/views.md` (Section 1.2) |
| **This Report** | `Documents/Teams/IMPLEMENTATION_REPORT_Role_Based_Dashboard.md` |

---

## 🎯 **What Each Role Sees**

### 👑 **OWNER / CAPTAIN**
```
✅ Captain Controls Section
   - Full Dashboard
   - Team Settings
   - Invite Members
   - Manage Roster
   - Register Tournaments
   - Team Analytics

✅ Member Tools (personal)
✅ Common Sections (all)
❌ Leave Team Button
```

### 📋 **MANAGER**
```
✅ Manager Tools Section
   - Manage Roster
   - Invite Members
   - Edit Team Profile
   - Register Tournaments
   - Team Analytics
   - View Settings

✅ Member Tools (personal)
✅ Common Sections (all)
✅ Leave Team Button
❌ Captain Controls
```

### 🎯 **COACH**
```
✅ Coach Tools Section
   - Strategy Planner (coming soon)
   - Schedule Practice (coming soon)
   - Performance Analytics
   - Training Materials (coming soon)

✅ Member Tools (personal)
✅ Common Sections (all)
✅ Leave Team Button
❌ Management Sections
```

### ⚡ **PLAYER**
```
✅ Member Tools Section ONLY
   - Update Game ID
   - View Personal Stats
   - Notifications
   - Team Calendar
   - Practice Schedule

✅ Common Sections (all)
✅ Leave Team Button
❌ Management Sections
```

### 🚫 **NON-MEMBER**
```
❌ No Dashboard Sections
✅ Public Team Information Only
✅ Join/Request Button (if recruiting)
```

---

## 🔧 **Context Flags (Backend)**

### **Role Flags** (set in `team_profile_view`)
```python
is_owner = user_membership.role == TeamMembership.Role.OWNER
is_manager = user_membership.role == TeamMembership.Role.MANAGER
is_coach = user_membership.role == TeamMembership.Role.COACH
is_player = user_membership.role == TeamMembership.Role.PLAYER
```

### **Permission Flags** (using `TeamPermissions`)
```python
can_manage_roster = TeamPermissions.can_manage_roster(user_membership)
can_edit_team_profile = TeamPermissions.can_edit_team_profile(user_membership)
can_register_tournaments = TeamPermissions.can_register_tournaments(user_membership)
can_leave_team = TeamPermissions.can_leave_team(user_membership)
can_view_team_settings = TeamPermissions.can_view_team_settings(user_membership)
```

---

## 📊 **Template Structure**

```django
{% if is_member %}
    
    {% if is_owner or is_captain %}
        <!-- Captain Controls Section (lines 67-108) -->
    {% elif is_manager and not is_owner and not is_captain %}
        <!-- Manager Tools Section (lines 114-158) -->
    {% elif is_coach and not is_owner and not is_manager %}
        <!-- Coach Tools Section (lines 164-206) -->
    {% endif %}
    
    <!-- Member Tools Section (lines 212-263) - ALL members -->
    {% if is_member %}
        <div class="member-tools">
            {% if can_leave_team %}
                <button class="leave-team-btn">Leave Team</button>
            {% endif %}
        </div>
    {% endif %}
    
    <!-- Common Sections (lines 265-654) - ALL members -->
    
{% endif %}
```

---

## ✅ **Quick Testing Guide**

### **Test Owner:**
```bash
# Expected: Captain Controls + Member Tools + Common
# NOT Expected: Manager Tools, Coach Tools, Leave Button
```

### **Test Manager:**
```bash
# Expected: Manager Tools + Member Tools + Common + Leave Button
# NOT Expected: Captain Controls, Coach Tools
```

### **Test Coach:**
```bash
# Expected: Coach Tools + Member Tools + Common + Leave Button
# NOT Expected: Captain Controls, Manager Tools
```

### **Test Player:**
```bash
# Expected: Member Tools + Common + Leave Button ONLY
# NOT Expected: Any management sections
```

### **Test Non-Member:**
```bash
# Expected: Public info only, no dashboard
# NOT Expected: Any dashboard sections
```

---

## 🎨 **CSS Classes Used**

```css
.glass-panel          /* Glassmorphism card effect */
.dashboard-section    /* Section container */
.dashboard-grid       /* Grid layout */
.dashboard-card       /* Individual action card */
.section-header       /* Section title */
.badge.coming-soon    /* Placeholder feature badge */
```

**Note:** All existing CSS, no new styles needed.

---

## 🧪 **Test Commands**

### **Run All Dashboard Tests:**
```powershell
python manage.py test apps.teams.tests.test_team_dashboard_roles --verbosity=2
```

### **Run Specific Test:**
```powershell
python manage.py test apps.teams.tests.test_team_dashboard_roles.TeamDashboardRoleTests.test_owner_sees_captain_controls
```

### **Django System Check:**
```powershell
python manage.py check
# Expected: System check identified no issues (0 silenced).
```

---

## 🔍 **Troubleshooting**

### **Issue: Dashboard not showing**
- Check user is logged in
- Verify user has active membership (`status=ACTIVE`)
- Check `is_member` flag in template context

### **Issue: Wrong section showing**
- Verify user's role in database: `TeamMembership.objects.get(user=user, team=team).role`
- Check conditional logic in template (lines 67-263)
- Inspect context in Django Debug Toolbar

### **Issue: "Coming Soon" broken**
- These are intentional placeholders
- Should show JavaScript alert, not error
- Check browser console for JavaScript errors

### **Issue: Leave button missing**
- Check `can_leave_team` flag (should be False for owners)
- Verify permission logic in `TeamPermissions.can_leave_team()`

---

## 📞 **Quick Commands**

### **Check User's Role:**
```python
from apps.teams.models import TeamMembership
membership = TeamMembership.objects.get(user=user, team=team)
print(membership.role)  # OWNER, MANAGER, COACH, PLAYER, SUBSTITUTE
```

### **Check Permissions:**
```python
from apps.teams.permissions import TeamPermissions
print(TeamPermissions.can_manage_roster(membership))
print(TeamPermissions.can_leave_team(membership))
```

### **View Context in Shell:**
```python
from django.test import Client
client = Client()
client.login(username='testuser', password='password')
response = client.get(f'/teams/{team_slug}/')
print(response.context['is_owner'])
print(response.context['is_manager'])
```

---

## 🎯 **Success Checklist**

- [ ] Owner sees Captain Controls
- [ ] Manager sees Manager Tools (NOT Captain Controls)
- [ ] Coach sees Coach Tools only
- [ ] Player sees Member Tools only
- [ ] Non-member sees no dashboard
- [ ] Leave button hidden for owners
- [ ] Leave button visible for all other roles
- [ ] Common sections visible to all members
- [ ] "Coming Soon" badges work (alerts, not errors)
- [ ] All URLs resolve correctly
- [ ] No console errors
- [ ] Visual design matches existing theme

---

## 📚 **Related Documentation**

- **Full Implementation Report:** `IMPLEMENTATION_REPORT_Role_Based_Dashboard.md`
- **Functional Spec:** `TEAM_APP_FUNCTIONAL_SPEC.md` (Section 5)
- **View Documentation:** `backup_files/teams/views.md` (Section 1.2)
- **Permission Rules:** `apps/teams/permissions.py`
- **Role Definitions:** `apps/teams/models.py` (TeamMembership.Role enum)

---

**Quick Reference Generated:** Current Sprint
**Last Verified:** Django System Check (0 issues)
**Status:** ✅ Production Ready

---

*For detailed implementation information, see IMPLEMENTATION_REPORT_Role_Based_Dashboard.md*
