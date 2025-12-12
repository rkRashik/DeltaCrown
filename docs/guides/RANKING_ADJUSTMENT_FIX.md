# Team Ranking Adjustment Fix

## Issue
Quick Adjustments and Custom Adjustment buttons in Team admin change page were not working.

## Root Cause
The custom template `templates/admin/teams/team/change_form.html` had complete JavaScript implementation for:
- Quick adjustment buttons (+10, +25, +50, +100, -10, -25, -50)
- Custom adjustment input
- Recalculate points button
- Auto-refresh points display

However, the backend URL handlers were completely missing from `TeamAdmin` class.

## Solution Implemented

### 1. Added Custom URL Routing in TeamAdmin

Added `get_urls()` method to register three custom admin endpoints:
- `POST /admin/teams/team/<id>/adjust-points/` - Manual point adjustments
- `POST /admin/teams/team/<id>/recalculate-points/` - Recalculate from criteria
- `GET /admin/teams/team/<id>/get-points/` - Get current points (for auto-refresh)

### 2. Created View Methods

**`adjust_points_view(request, team_id)`**
- Accepts POST with JSON payload: `{points_adjustment: int, reason: string}`
- Calls `ranking_service.adjust_team_points()` from TeamRankingService
- Returns JSON: `{success: bool, new_total: int, old_total: int, points_change: int, error: string}`
- Records adjustment in TeamRankingHistory with admin user

**`recalculate_points_view(request, team_id)`**
- Accepts POST request (no payload needed)
- Calls `ranking_service.recalculate_team_points()` to recalculate from scratch
- Returns same JSON format as adjust_points_view
- Useful when criteria change or data is out of sync

**`get_points_view(request, team_id)`**
- Accepts GET request
- Returns current team points: `{success: bool, points: int}`
- Used by auto-refresh mechanism (every 30 seconds)

### 3. Added Required Imports

Added to `apps/teams/admin.py`:
```python
from django.urls import path
from django.http import JsonResponse
import json
```

### 4. Updated Template Reference

Added `change_form_template` to TeamAdmin:
```python
change_form_template = 'admin/teams/team/change_form.html'
```

## Testing

All endpoints use TeamRankingService which:
- Uses database transactions for atomicity
- Records all changes in TeamRankingHistory
- Updates TeamRankingBreakdown automatically
- Logs all operations

### Test Cases
1. **Quick Adjustments**: Click preset buttons (+10, -25, etc.)
2. **Custom Adjustment**: Enter custom value (e.g., 150) with reason
3. **Recalculate Points**: Force full recalculation from criteria
4. **Auto-refresh**: Points update automatically every 30 seconds

### Expected Behavior
- Success: Green message, points update, page auto-refresh after 2 seconds
- Error: Red message with error details
- History: All changes recorded in TeamRankingHistory with admin user

## Files Modified
- `apps/teams/admin.py` - Added get_urls() and three view methods

## Verification
```bash
python manage.py check
# System check identified no issues (0 silenced).
```

## Next Steps
1. Test Quick Adjustments buttons in admin at `/admin/teams/team/<id>/change/`
2. Verify points update in database and display
3. Check TeamRankingHistory records are created
4. Confirm auto-refresh works (wait 30 seconds on change page)
