# 🎮 Tournament Registration - Quick Test Guide

## ✅ Pre-Flight Checklist

1. **Clear Browser Cache**
   ```
   Press: Ctrl + Shift + R (Windows/Linux)
   Press: Cmd + Shift + R (Mac)
   ```

2. **Verify Static Files Collected**
   ```powershell
   python manage.py collectstatic --noinput
   ```

3. **Check Dev Server Running**
   ```powershell
   python manage.py runserver
   ```

## 🔍 Testing Steps

### Test 1: Tournament Hub Page
1. Navigate to: `http://localhost:8000/tournaments/`
2. Open Developer Tools (F12)
3. Go to **Console** tab
4. Look for: `[Tournament Card Dynamic] Initializing...`
5. Check each tournament card has valid slug (not "undefined")
6. Click any "Register Now" button
7. ✅ **Expected**: Redirect to `/tournaments/register-modern/ACTUAL-SLUG/`
8. ❌ **Failed**: Still shows `/tournaments/register-modern/undefined/`

### Test 2: Game-Specific Listing
1. Navigate to: `http://localhost:8000/tournaments/by-game/efootball/`
2. Repeat steps 2-8 from Test 1

### Test 3: Tournament Detail Page  
1. Navigate to any tournament detail page
2. Open Developer Tools Console
3. Look for: `[Tournament Detail] Loading buttons for slug: ACTUAL-SLUG`
4. Check all 3 button locations load:
   - Hero section (top banner)
   - Sidebar (right side)
   - Mobile sticky (bottom)
5. Click any button
6. ✅ **Expected**: Redirect to registration page with correct slug
7. ❌ **Failed**: 404 or undefined slug

## 🐛 Debug Console Commands

### Check if JavaScript is loaded:
```javascript
// Should return object with functions
console.log(window.TournamentCardDynamic);
console.log(window.TournamentDetailModern);
```

### Manually test API:
```javascript
// Replace 'efootball-champions' with actual slug
fetch('/tournaments/api/efootball-champions/register/context/')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error);
```

### Check data attributes:
```javascript
// Should show actual slug, not undefined
document.querySelectorAll('[data-tournament-slug]').forEach(el => {
  console.log(el.dataset.tournamentSlug);
});
```

## 📊 Expected Console Output

### ✅ Correct Output:
```
[Tournament Card Dynamic] Initializing...
[Tournament Card Dynamic] Found 5 containers
[Tournament Card Dynamic] Container 1: { slug: "mlbb-championship-2025", element: article.dc-card }
[Tournament Card Dynamic] Container 2: { slug: "efootball-champions", element: article.dc-card }
[Tournament Detail] Loading buttons for slug: efootball-champions
[Tournament Detail] API Response: { success: true, context: {...} }
[Tournament Detail] Rendering button: { slug: "efootball-champions", state: "register", text: "Register Now" }
```

### ❌ Error Output:
```
[Tournament Card Dynamic] Container 1: { slug: undefined, element: article.dc-card }
Tournament slug is missing or invalid: undefined
[Tournament Detail] Loading buttons for slug: undefined
[Tournament Detail] Failed to load registration context: TypeError: ...
```

## 🎯 Button States Reference

| Button Text | Icon | Color | Clickable | State |
|------------|------|-------|-----------|-------|
| Register Now | 🙋 | Primary | ✅ | `register` |
| Already Registered | ✅ | Green | ❌ | `registered` |
| Request Approval | 📤 | Orange | ✅ | `request_approval` |
| Approval Pending | ⏳ | Yellow | ❌ | `request_pending` |
| Registration Closed | 🔒 | Gray | ❌ | `closed` |
| Tournament Started | 🏁 | Gray | ❌ | `started` |
| Tournament Full | 👥 | Gray | ❌ | `full` |
| Need Team | ⚠️ | Red | ❌ | `no_team` |

## 🔧 Quick Fixes

### Issue: Cached JavaScript
```powershell
# Re-collect static files
python manage.py collectstatic --noinput --clear

# Hard refresh browser
Ctrl + Shift + R
```

### Issue: 404 on API call
```python
# Check tournament exists
python manage.py shell
>>> from apps.tournaments.models import Tournament
>>> Tournament.objects.filter(slug='YOUR-SLUG').exists()
```

### Issue: No console logs
```
1. Check Network tab in DevTools
2. Filter by: tournament-card-dynamic.js
3. Verify: Status 200, Size > 0
4. Check version: ?v=4 in URL
```

## 📁 File Versions

Current version: **v=4**

Files should load as:
- `tournament-card-dynamic.js?v=4`
- `tournament-detail-modern.js?v=4`

If browser loads older version (v=1, v=2, v=3), **clear cache**.

## 🚨 Critical Checks

- [ ] `ctx.t.slug` has value in template (not empty)
- [ ] `data-tournament-slug="{{ ctx.t.slug }}"` in HTML
- [ ] API endpoint `/tournaments/api/{slug}/register/context/` returns 200
- [ ] JavaScript files loaded with `?v=4` parameter
- [ ] No JavaScript errors in console
- [ ] Button URLs contain actual slug, not "undefined"

## 📞 Need Help?

Check these files for reference:
1. `docs/TOURNAMENT_REGISTRATION_TROUBLESHOOTING.md` - Detailed troubleshooting
2. `docs/MODERN_REGISTRATION_INTEGRATION_GUIDE.md` - Implementation guide
3. `docs/MODERN_REGISTRATION_INDEX.md` - System overview

---

**Version**: 4.0  
**Last Updated**: October 2, 2025  
**Status**: ✅ Ready for Testing
