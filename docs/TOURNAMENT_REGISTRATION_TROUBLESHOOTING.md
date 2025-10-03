# Tournament Registration System - Troubleshooting Guide

## Issue: "undefined" slug in registration URL

### Problem
When clicking "Register Now" buttons, users were redirected to:
```
/tournaments/register-modern/undefined/
```

This resulted in a 404 error: "No Tournament matches the given query."

### Root Cause
The JavaScript code was trying to extract the tournament slug from the API response using `context.tournament_slug`, but the `RegistrationContext.to_dict()` method in the backend doesn't include this field.

### Solution Applied

#### 1. Updated `tournament-card-dynamic.js`
- **Changed**: `renderButton()` function now receives `slug` as a parameter
- **Changed**: `loadRegistrationButton()` passes the slug from HTML data attribute
- **Before**: `const slug = context.tournament_slug;` (undefined)
- **After**: `function renderButton(container, context, slug, variant)` (passed as param)

#### 2. Updated `tournament-detail-modern.js`
- **Changed**: `renderDetailButton()` function now receives `slug` as a parameter
- **Changed**: `loadRegistrationButtons()` passes slug to render function
- **Before**: `const slug = context.tournament_slug;` (undefined)
- **After**: `function renderDetailButton(container, context, slug, variant)` (passed as param)

#### 3. Updated Cache Busters
- All templates now use `?v=4` to force browser refresh

### Files Modified

1. **`static/js/tournament-card-dynamic.js`**
   - Line ~33: Updated `loadRegistrationButton()` to pass slug
   - Line ~50: Updated `renderButton()` signature to accept slug parameter
   - Removed reliance on `context.tournament_slug`

2. **`static/js/tournament-detail-modern.js`**
   - Line ~29: Updated `loadRegistrationButtons()` to pass slug
   - Line ~63: Updated `renderDetailButton()` signature to accept slug parameter
   - Added console logging for debugging
   - Removed reliance on `context.tournament_slug`

3. **Templates**
   - `templates/tournaments/hub.html` - Updated to `?v=4`
   - `templates/tournaments/list_by_game.html` - Updated to `?v=4`
   - `templates/tournaments/detail.html` - Updated to `?v=4`

### How It Works Now

1. **HTML provides slug**
   ```html
   <div data-tournament-slug="{{ ctx.t.slug }}">
   ```

2. **JavaScript reads slug from HTML**
   ```javascript
   const slug = container.dataset.tournamentSlug;
   ```

3. **API is called with slug**
   ```javascript
   fetch(`/tournaments/api/${slug}/register/context/`)
   ```

4. **Slug is passed through to render function**
   ```javascript
   renderButton(container, data.context, slug);
   ```

5. **Button uses slug in href**
   ```html
   <a href="/tournaments/register-modern/${slug}/">
   ```

### Testing Checklist

- [ ] Hard refresh browser (Ctrl + Shift + R)
- [ ] Visit tournament hub page
- [ ] Check browser console for debug logs
- [ ] Verify slug values are not "undefined"
- [ ] Click "Register Now" button
- [ ] Confirm redirect to correct URL with actual slug
- [ ] Test on tournament detail pages
- [ ] Test on game listing pages

### Debug Console Output

When working correctly, you should see:
```
[Tournament Card Dynamic] Initializing...
[Tournament Card Dynamic] Found 3 containers
[Tournament Card Dynamic] Container 1: { slug: "efootball-champions", element: ... }
[Tournament Detail] Loading buttons for slug: efootball-champions
[Tournament Detail] API Response: { success: true, context: {...} }
[Tournament Detail] Rendering button: { slug: "efootball-champions", state: "register", text: "Register Now" }
```

### Common Issues

#### Issue: Still seeing "undefined"
**Solution**: Hard refresh with Ctrl + Shift + R or clear browser cache

#### Issue: API returns 404
**Solution**: Check that tournament exists in database with valid slug:
```python
python manage.py shell
from apps.tournaments.models import Tournament
Tournament.objects.values('slug', 'name')
```

#### Issue: No console logs
**Solution**: Check that JavaScript files are loaded:
- Open Network tab in DevTools
- Look for `tournament-card-dynamic.js?v=4`
- Look for `tournament-detail-modern.js?v=4`
- Verify they return 200 OK status

#### Issue: Button stays in skeleton state
**Solution**: Check API endpoint is accessible:
1. Open browser console
2. Run: `fetch('/tournaments/api/SLUG/register/context/').then(r => r.json()).then(console.log)`
3. Replace SLUG with actual tournament slug

### Backend API Structure

The API endpoint `/tournaments/api/<slug>/register/context/` returns:

```json
{
  "success": true,
  "context": {
    "can_register": true,
    "button_state": "register",
    "button_text": "Register Now",
    "reason": "",
    "is_team_event": true,
    "is_captain": false,
    "team_registered": false,
    "already_registered": false,
    "slots_available": true,
    "requires_payment": false,
    "has_team": true,
    "team_name": "My Team",
    "has_pending_request": false
  }
}
```

**Note**: `tournament_slug` is NOT included in the response, which is why we pass it from the HTML.

### Button States

| State | Description | Clickable | URL |
|-------|-------------|-----------|-----|
| `register` | Open for registration | ✅ | `/tournaments/register-modern/{slug}/` |
| `registered` | Already registered | ❌ | - |
| `request_approval` | Need captain approval | ✅ | `/tournaments/register-modern/{slug}/` |
| `request_pending` | Approval pending | ❌ | - |
| `closed` | Registration closed | ❌ | - |
| `started` | Tournament started | ❌ | - |
| `full` | Tournament full | ❌ | - |
| `no_team` | No team (for team events) | ❌ | - |

### Future Improvements

1. **Add tournament_slug to API response**
   ```python
   # In RegistrationContext.to_dict()
   def to_dict(self) -> Dict[str, Any]:
       return {
           # ... existing fields ...
           "tournament_slug": self.tournament.slug,
       }
   ```

2. **Add retry logic for failed API calls**
3. **Add loading state timeout (5 seconds)**
4. **Add explicit error messages for each failure mode**

### Related Files

- `apps/tournaments/services/registration_service.py` - Backend logic
- `apps/tournaments/views/registration_modern.py` - API endpoints
- `apps/tournaments/views/public.py` - Tournament detail view
- `templates/tournaments/partials/_tournament_card.html` - Card component
- `static/siteui/css/tournament-card-modern.css` - Button styles

---

**Last Updated**: October 2, 2025
**Version**: 4.0
**Status**: ✅ Fixed
