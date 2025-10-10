# Quick Testing Guide - Frontend Integration

## 🚀 Start Testing in 5 Minutes

### Prerequisites
- Python 3.11+ installed
- PostgreSQL running
- Virtual environment activated

---

## Step 1: Start the Server

```powershell
# Navigate to project directory
cd "G:\My Projects\WORK\DeltaCrown"

# Activate virtual environment (if not already active)
.venv\Scripts\Activate.ps1

# Start Django development server
python manage.py runserver
```

**Expected Output:**
```
System check identified no issues (0 silenced).
October 10, 2025 - 10:30:00
Django version 4.2.23, using settings 'deltacrown.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

---

## Step 2: Test Dashboard → Teams Flow

### 2.1 Login
1. Open browser: `http://localhost:8000/`
2. Click "Login" or go to `/accounts/login/`
3. Enter credentials
4. Should redirect to homepage or dashboard

### 2.2 Dashboard
1. Go to: `http://localhost:8000/dashboard/`
2. **Verify you see:**
   - ✅ "Welcome, [Your Name]" header
   - ✅ "My Teams" widget (with team logos or empty state)
   - ✅ "Team Invites" widget (if any pending)
   - ✅ "Upcoming Matches" widget
   - ✅ "My Registrations" widget
   - ✅ "Create Team" button (top right)

### 2.3 Create Team
1. Click **"Create Team"** button
2. Should navigate to: `/teams/create/`
3. Fill in the form:
   - Team Name: "Test Warriors"
   - Team Tag: "TEST"
   - Game: Select "Valorant"
   - Bio: "Testing frontend integration"
4. Click **"Create Team"**
5. **Verify:**
   - ✅ Success toast notification appears
   - ✅ Redirects to team detail page: `/teams/test-warriors/`
   - ✅ Team logo/banner visible
   - ✅ Your name shows as Captain

### 2.4 Navigate Back to Dashboard
1. Click **"Dashboard"** in navbar
2. **Verify:**
   - ✅ New team appears in "My Teams" widget
   - ✅ Team logo displays correctly
   - ✅ Member count shows "1/5"

---

## Step 3: Test Tournament Registration Flow

### 3.1 Browse Tournaments
1. Go to: `http://localhost:8000/tournaments/`
2. **Verify:**
   - ✅ Tournament cards display
   - ✅ Entry fees visible
   - ✅ Prize pools shown
   - ✅ "Register" buttons visible

### 3.2 Register Team
1. Click **"Register"** on any open tournament
2. Should navigate to: `/tournaments/{slug}/register/`
3. **Verify registration page:**
   - ✅ Tournament name displayed
   - ✅ Breadcrumbs: Tournaments › [Name] › Register
   - ✅ Entry fee chip visible
   - ✅ Team selector dropdown appears

4. **Select your team:**
   - Choose "Test Warriors" from dropdown
   - ✅ Roster should auto-load below
   - ✅ Your profile should appear in roster preview

5. **Submit registration:**
   - Click **"Confirm Registration"**
   - ✅ Success modal should appear
   - ✅ Confirmation number displayed
   - ✅ Option to view registration status

### 3.3 Verify Dashboard Update
1. Go back to: `/dashboard/`
2. **Verify:**
   - ✅ New registration appears in "My Registrations" widget
   - ✅ Status badge shows (Pending/Confirmed)
   - ✅ Tournament name is clickable

---

## Step 4: Test Team Invite Flow

### 4.1 Invite a Member (As Captain)
1. Go to your team: `/teams/test-warriors/`
2. Click **"Manage"** or **"Invite Member"**
3. Navigate to: `/teams/test-warriors/invite/`
4. **Fill invite form:**
   - Email/Username: Enter another user's email
   - Role: Select "Player"
   - Click **"Send Invite"**
5. **Verify:**
   - ✅ Success toast: "Invite sent!"
   - ✅ Email sent to invited user
   - ✅ Invite appears in pending list

### 4.2 Accept Invite (As Invited User)
1. Logout current user
2. Login as invited user
3. Go to: `/dashboard/`
4. **Verify in "Team Invites" widget:**
   - ✅ Invite card displays
   - ✅ Team name visible
   - ✅ Inviter name shown
   - ✅ "Accept" button present

5. **Click "Accept"**
   - ✅ Success toast: "You joined [Team Name]!"
   - ✅ Invite disappears from widget
   - ✅ Team now appears in "My Teams"

### 4.3 Verify Roster Update
1. Go to team page: `/teams/test-warriors/`
2. **Verify:**
   - ✅ New member appears in roster
   - ✅ Member count updated: "2/5"
   - ✅ Role badge shows correctly

---

## Step 5: Mobile Responsiveness Test

### 5.1 Desktop → Mobile View
1. Open Chrome DevTools (F12)
2. Click device toolbar icon (or Ctrl+Shift+M)
3. Select: **iPhone 12 Pro**

### 5.2 Test Dashboard
1. Navigate to: `/dashboard/`
2. **Verify:**
   - ✅ Widgets stack vertically
   - ✅ "Create Team" button accessible
   - ✅ Team logos don't overflow
   - ✅ All text readable (no tiny fonts)

### 5.3 Test Team Creation
1. Go to: `/teams/create/`
2. **Verify:**
   - ✅ Form fields stack vertically
   - ✅ Inputs are tap-friendly (44px min)
   - ✅ Wizard steps visible
   - ✅ Submit button reachable

### 5.4 Test Tournament Registration
1. Go to: `/tournaments/{slug}/register/`
2. **Verify:**
   - ✅ Breadcrumbs collapse or wrap
   - ✅ Team selector dropdown works
   - ✅ Roster cards stack
   - ✅ Confirm button fixed at bottom

### 5.5 Rotate to Landscape
1. Rotate device (Ctrl+Shift+R in DevTools)
2. **Verify:**
   - ✅ Navigation menu adjusts
   - ✅ Content remains readable
   - ✅ No horizontal scroll

---

## Step 6: Test Navigation Links

### 6.1 Global Navigation
Test each navbar link:
- ✅ **Home** → `/` (homepage)
- ✅ **Tournaments** → `/tournaments/` (hub)
- ✅ **Teams** → `/teams/` (hub)
- ✅ **Dashboard** → `/dashboard/` (user dashboard)
- ✅ **Profile** → `/profile/` or `/user-profile/`

### 6.2 Breadcrumb Navigation
1. Go to: `/tournaments/{slug}/register/`
2. Click breadcrumb: **"Tournaments"**
   - ✅ Should go to `/tournaments/hub/`
3. Click breadcrumb: **"[Tournament Name]"**
   - ✅ Should go to `/tournaments/{slug}/`

### 6.3 Widget Links
From dashboard, test:
- ✅ "My Teams" → "View All" → `/teams/hub/`
- ✅ Team card → `/teams/{slug}/`
- ✅ "Team Invites" → "View All" → `/teams/invites/`
- ✅ "Upcoming Matches" → "View All" → `/dashboard/my-matches/`
- ✅ "My Registrations" → Tournament name → `/tournaments/{slug}/`

---

## Step 7: Test Toast Notifications

### 7.1 Success Notifications
**Trigger:** Create team, send invite, accept invite, register for tournament

**Expected:**
- ✅ Green toast appears (top-right or bottom-center)
- ✅ Success icon (checkmark)
- ✅ Message displays clearly
- ✅ Auto-dismisses after 5 seconds
- ✅ Can manually close with X button

### 7.2 Error Notifications
**Trigger:** Submit empty form, exceed roster limit, duplicate team name

**Expected:**
- ✅ Red toast appears
- ✅ Error icon (exclamation)
- ✅ Error message explains issue
- ✅ Stays visible until closed

### 7.3 Info Notifications
**Trigger:** Generic actions (e.g., "Copied to clipboard")

**Expected:**
- ✅ Blue toast appears
- ✅ Info icon (i)
- ✅ Message clear and concise

---

## Step 8: Browser Console Check

### 8.1 Open Developer Tools
1. Press **F12**
2. Go to **Console** tab

### 8.2 Check for Errors
**Should see:**
- ✅ No 404 errors (missing JS/CSS files)
- ✅ No CORS errors
- ✅ No "Uncaught TypeError" errors
- ✅ No "undefined is not a function" errors
- ✅ No jQuery errors (if using jQuery)

**Warnings are OK:**
- ⚠️ "Synchronous XMLHttpRequest" (legacy)
- ⚠️ Deprecation warnings (future browser changes)

### 8.3 Network Tab
1. Go to **Network** tab
2. Refresh page (Ctrl+R)
3. **Verify:**
   - ✅ All files load (green 200 status)
   - ✅ No failed requests (red 404/500)
   - ✅ Total page size < 5MB
   - ✅ Load time < 3 seconds (local)

---

## Step 9: Test Email Notifications (Optional)

### 9.1 Configure Test Email Backend
```python
# settings.py (for testing only)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

### 9.2 Send Test Invite
1. Invite a member to team
2. **Check terminal/console:**
   - ✅ Email content appears in console
   - ✅ Subject line correct
   - ✅ Invite link present
   - ✅ Expiration date shown

### 9.3 Check Email Content
**Should include:**
- Team name
- Inviter name
- Accept link: `/invites/{token}/accept/`
- Decline link: `/invites/{token}/decline/`
- Expiration warning

---

## Step 10: Test Edge Cases

### 10.1 Empty States
1. **New user with no teams:**
   - Dashboard "My Teams" → ✅ Empty state with "Create Team" CTA
2. **No pending invites:**
   - Dashboard "Team Invites" → ✅ Empty state "No pending invites"
3. **No matches:**
   - Dashboard "Upcoming Matches" → ✅ Empty state with calendar icon

### 10.2 Error Handling
1. **Create team with existing name:**
   - ✅ Form shows error: "Team name already exists"
2. **Invite same user twice:**
   - ✅ Toast error: "User already invited"
3. **Register for closed tournament:**
   - ✅ Button disabled or shows "Registration Closed"

### 10.3 Permission Checks
1. **Non-captain tries to invite:**
   - ✅ "Invite Member" button hidden/disabled
2. **Non-member tries to view team chat:**
   - ✅ Redirect or permission denied message

---

## 🐛 Common Issues & Fixes

### Issue: "Page not found (404)"
**Fix:**
```bash
# Check URL patterns
python manage.py show_urls | grep teams

# Verify namespace
# URLs should be: teams:hub, teams:create, teams:detail
```

### Issue: "CSRF verification failed"
**Fix:**
```django-html
<!-- Add to forms -->
{% csrf_token %}
```

### Issue: "Static files not loading"
**Fix:**
```bash
# Collect static files
python manage.py collectstatic

# Check settings.py
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
```

### Issue: "Template does not exist"
**Fix:**
```python
# Check TEMPLATES in settings.py
'DIRS': [BASE_DIR / 'templates'],
```

### Issue: "No toast notifications appear"
**Fix:**
```django-html
<!-- Verify in base.html -->
<script src="{% static 'siteui/js/notifications.js' %}"></script>

<!-- Check for messages block -->
{% if messages %}
  <!-- Django messages here -->
{% endif %}
```

---

## ✅ Success Criteria

**Your integration is successful if:**

1. ✅ Dashboard loads without errors
2. ✅ All 4+ widgets display correctly
3. ✅ "Create Team" flow works end-to-end
4. ✅ Team appears in dashboard after creation
5. ✅ Tournament registration completes successfully
6. ✅ Team invite can be sent and accepted
7. ✅ Mobile view is fully functional
8. ✅ No JavaScript console errors
9. ✅ Toast notifications appear for all actions
10. ✅ All links navigate correctly

---

## 📊 Testing Checklist

Print this and check off as you test:

```
Dashboard Tests:
[ ] Login successful
[ ] Dashboard loads
[ ] "My Teams" widget displays
[ ] "Team Invites" widget displays
[ ] "Upcoming Matches" widget displays
[ ] "My Registrations" widget displays
[ ] "Create Team" button works

Team Flow Tests:
[ ] Create team form loads
[ ] Team creation succeeds
[ ] Team appears in dashboard
[ ] Team detail page loads
[ ] Team manage page accessible
[ ] Invite member form works
[ ] Invite email sent

Tournament Flow Tests:
[ ] Tournament hub loads
[ ] Tournament detail page loads
[ ] Registration form accessible
[ ] Team selector works
[ ] Roster auto-loads
[ ] Registration completes
[ ] Dashboard shows registration

Mobile Tests:
[ ] Dashboard responsive on mobile
[ ] Team creation works on mobile
[ ] Tournament registration works on mobile
[ ] Navigation menu collapses
[ ] All buttons tap-friendly

Integration Tests:
[ ] Dashboard → Teams link works
[ ] Teams → Tournaments link works
[ ] Tournament → Teams link works
[ ] Breadcrumbs work
[ ] Global nav works
[ ] Toast notifications appear
[ ] No console errors
```

---

## 🎉 Next Steps After Testing

If all tests pass:
1. ✅ Mark integration as complete
2. ✅ Document any custom configurations
3. ✅ Prepare for production deployment
4. ✅ Set up monitoring and error tracking
5. ✅ Train team on new features

If issues found:
1. 🐛 Document the issue
2. 🔍 Check relevant documentation
3. 🛠️ Apply fixes from "Common Issues" section
4. 🔄 Re-test
5. 📝 Update this guide if needed

---

## 📞 Need Help?

**Documentation:**
- `FRONTEND_INTEGRATION_COMPLETE.md` - Full integration guide
- `README.md` - Project overview
- Django docs: https://docs.djangoproject.com/

**Check Logs:**
```bash
# Django console output
# Browser console (F12)
# Database logs (if applicable)
```

---

**Testing Time:** ~15-20 minutes  
**Difficulty:** Beginner-friendly  
**Prerequisites:** Running Django server  

Happy Testing! 🚀
