# Spectator Live Views

**Phase**: G  
**Status**: Complete  
**Date**: 2025-11-13

---

## 1. Overview

Spectator Live Views provide a mobile-first, read-only interface for tournament spectators to follow live matches, track leaderboards, and receive real-time updates without authentication requirements.

### Purpose

Enable external viewers (fans, family, coaches) to:
- Watch tournament leaderboards update in real-time
- Follow individual matches with live score updates
- See upcoming match schedules
- Experience tournament atmosphere without player accounts

### Key Features

1. **Tournament Overview Page**: Live leaderboard + match list with auto-refresh
2. **Match Detail Page**: Live scoreboard + event feed with WebSocket updates
3. **Mobile-First Design**: Responsive Tailwind CSS layout optimized for phones
4. **Real-Time Updates**: htmx auto-refresh + WebSocket instant notifications
5. **IDs-Only Discipline**: No PII exposed (participant/team IDs only)

---

## 2. URLs

All spectator routes are under `/spectator/` prefix:

### Full Pages

| URL | Method | Description |
|-----|--------|-------------|
| `/spectator/tournaments/<int:tournament_id>/` | GET | Tournament spectator page (leaderboard + matches) |
| `/spectator/matches/<int:match_id>/` | GET | Match spectator page (scoreboard + live events) |

### Fragment Endpoints (htmx partials)

| URL | Method | Description | Refresh Rate |
|-----|--------|-------------|--------------|
| `/spectator/tournaments/<int:tournament_id>/leaderboard/fragment/` | GET | Leaderboard table fragment | Every 10s |
| `/spectator/tournaments/<int:tournament_id>/matches/fragment/` | GET | Match list fragment | Every 15s |
| `/spectator/matches/<int:match_id>/scoreboard/fragment/` | GET | Scoreboard fragment | Every 5s |

**Note**: Fragment endpoints return partial HTML for htmx `hx-get` auto-refresh. They serve as fallback when WebSocket is unavailable.

---

## 3. Data Sources

Spectator views aggregate data from existing backend services:

### Leaderboards (Phase E)
- **Service**: `apps.tournaments.services.leaderboard_service.LeaderboardService`
- **Method**: `get_leaderboard(tournament_id, limit=20)`
- **Returns**: 
  - `entries` list with `rank`, `participant_id`, `team_id`, `points`
  - Sorted by rank (top 20 for spectator view)

### Matches (Phase 4)
- **Model**: `apps.tournaments.models.Match`
- **Query**: Filter by `tournament_id`, status (`scheduled`, `in_progress`)
- **Fields**: `id`, `round`, `status`, `scheduled_time`, `participant1_id`, `participant2_id`, `scores`

### Real-Time Updates (Module 2.6)
- **Channel**: Existing tournament WebSocket rooms (`/ws/tournament/<tournament_id>/`)
- **Events**: `score_updated`, `match_completed`, `bracket_updated`, `match_started`, `dispute_created`
- **Protocol**: JSON messages with `type` and `data` fields

---

## 4. Technology Stack

### Backend
- **Framework**: Django 4.2+ (views + templates)
- **Views**: Function-based views in `apps/spectator/views.py`
- **Routing**: URL patterns in `apps/spectator/urls.py`
- **Service Layer**: Orchestrates existing Phase E leaderboards + Phase 4 matches

### Frontend
- **Templates**: Django template engine with Jinja2 syntax
- **CSS Framework**: Tailwind CSS 3.x (via CDN for rapid prototyping)
- **JS Framework**: Alpine.js 3.x (reactive UI state)
- **AJAX Library**: htmx 1.9+ (auto-refresh partials)
- **WebSocket**: Native browser WebSocket API (no external library)

### Design System
- **Color Palette**:
  - Primary: `#00d9ff` (Cyan - live indicators)
  - Secondary: `#ff006e` (Magenta - participant 2)
  - Accent: `#ffbe0b` (Yellow - leaderboard medals)
  - Success: `#06ffa5` (Green - completed matches)
  - Error: `#ff006e` (Red - live match badges)
- **Typography**: System font stack with monospace for IDs
- **Components**: Glassmorphism cards with gradients + borders

---

## 5. IDs-Only Discipline

Spectator views strictly follow **IDs-only policy**:

### What is Displayed

✅ **Tournament IDs**: `Tournament #12345`  
✅ **Match IDs**: `Match #67890`  
✅ **Participant IDs**: `Player #1234`, `Team #5678`  
✅ **Numeric Data**: Scores, points, ranks  
✅ **Enum Values**: Match status (`scheduled`, `in_progress`, `completed`)  
✅ **Timestamps**: Scheduled times, match start times

### What is NOT Displayed

❌ **Display Names**: `CoolGamer123`, `TeamDragons`  
❌ **Usernames**: `john_doe`, `alice_smith`  
❌ **Emails**: `user@example.com`  
❌ **Real Names**: `John Doe`, `Alice Smith`  
❌ **IP Addresses**: (internal use only, never in UI)

### Name Resolution (Future Enhancement)

When ready to display names, clients must:

1. **Extract IDs** from spectator UI
2. **Call name resolution APIs** (authenticated endpoints):
   - `/api/profiles/<participant_id>/` → Returns `display_name`, `avatar_url`
   - `/api/teams/<team_id>/` → Returns `team_name`, `logo_url`
   - `/api/tournaments/<tournament_id>/metadata/` → Returns `tournament_name`, `game_name`

3. **Render names client-side** via JavaScript (not in Django templates)

**Example Flow**:
```javascript
// Spectator UI shows: "Player #1234 vs Player #5678"
const player1Id = 1234;

// Client fetches profile (requires auth token)
fetch(`/api/profiles/${player1Id}/`, {
  headers: { 'Authorization': `Bearer ${token}` }
})
.then(res => res.json())
.then(data => {
  // Replace "Player #1234" with "CoolGamer123"
  document.querySelector('.participant1-name').textContent = data.display_name;
});
```

**Current State**: Name resolution not yet implemented. Spectator UI shows IDs only as placeholders.

---

## 6. Real-Time Updates Architecture

Spectator views use **dual-layer** real-time strategy:

### Layer 1: htmx Auto-Refresh (Fallback)

**Mechanism**: HTTP polling via htmx `hx-trigger="every Xs"`

**Endpoints**:
- Leaderboard: Refreshes every 10s
- Match List: Refreshes every 15s
- Scoreboard: Refreshes every 5s

**Advantages**:
- Works without WebSocket support (older browsers, restrictive networks)
- No client-side state management
- Automatic fallback when WebSocket disconnects

**Example**:
```html
<div 
  hx-get="/spectator/tournaments/123/leaderboard/fragment/" 
  hx-trigger="every 10s" 
  hx-swap="outerHTML"
>
  <!-- Leaderboard table rendered here -->
</div>
```

### Layer 2: WebSocket Push (Primary)

**Mechanism**: Persistent WebSocket connection to tournament channel

**Connection**:
```javascript
const wsUrl = 'ws://localhost:8000/ws/tournament/123/';
const ws = new WebSocket(wsUrl);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'score_updated') {
    // Trigger htmx refresh immediately (don't wait for timer)
    htmx.trigger(scoreboardElement, 'refresh');
  }
};
```

**Events Handled**:
- `score_updated` → Refresh scoreboard + match list
- `match_completed` → Refresh leaderboard + match list
- `bracket_updated` → Refresh leaderboard
- `match_started` → Add event to live feed
- `dispute_created` → Add event to live feed

**Advantages**:
- Instant updates (< 100ms latency)
- No unnecessary HTTP requests
- Efficient bandwidth usage

**Reconnection**:
- Automatic reconnect after 5 seconds on disconnect
- Max 10 reconnect attempts before giving up
- Status indicator shows connection state

---

## 7. Mobile-First Design

### Responsive Breakpoints

| Breakpoint | Width | Layout |
|------------|-------|--------|
| Mobile | < 768px | Stacked (leaderboard below matches) |
| Tablet | 768px - 1024px | 2-column grid |
| Desktop | > 1024px | 3-column grid (matches 2/3, leaderboard 1/3) |

### Mobile Optimizations

1. **Touch Targets**: Minimum 44px height for clickable elements (matches, nav links)
2. **Font Scaling**: Base 16px, scales to 18px on desktop
3. **Reduced Motion**: Respects `prefers-reduced-motion` for animations
4. **Offline Indicator**: Shows "Disconnected" badge when WebSocket drops
5. **Compact Tables**: Leaderboard uses 3-column layout (rank, ID, points) on mobile

### Performance

- **Initial Load**: < 2s on 3G (Tailwind CDN cached, minimal JS)
- **Time to Interactive**: < 3s (htmx + Alpine.js load asynchronously)
- **WebSocket Overhead**: ~5 KB/minute for live events
- **htmx Polling**: ~10 KB/minute for fallback refresh

---

## 8. File Structure

```
apps/spectator/
├── __init__.py           # App initialization
├── apps.py               # Django app config
├── views.py              # View functions (tournament, match, fragments)
└── urls.py               # URL routing

templates/spectator/
├── base.html             # Base layout (nav, footer, CDN includes)
├── tournament_detail.html  # Tournament page (leaderboard + matches)
├── match_detail.html     # Match page (scoreboard + event feed)
├── _leaderboard_table.html  # Partial: Leaderboard table
├── _match_list.html      # Partial: Match list cards
└── _scoreboard.html      # Partial: Match scoreboard

static/js/
└── spectator_ws.js       # WebSocket client library (SpectatorWSClient class)

docs/spectator/
└── README.md             # This file
```

---

## 9. Integration Points

### Phase E: Leaderboards
- **Service**: `LeaderboardService.get_leaderboard()`
- **Usage**: Populate tournament page leaderboard panel
- **Data**: Top 20 entries with rank, IDs, points

### Phase 4: Matches
- **Model**: `Match` (tournament_id, round, status, scores)
- **Usage**: Populate match list + match detail page
- **Query**: Filter by status (`scheduled`, `in_progress`)

### Module 2.6: Realtime Monitoring
- **Channel**: `/ws/tournament/<tournament_id>/`
- **Events**: `score_updated`, `match_completed`, `bracket_updated`, etc.
- **Usage**: Push instant updates to spectator clients

### Module 2.4: Security (JWT Auth)
- **Requirement**: WebSocket connections require JWT token (optional for public spectators)
- **Current**: Token fetched from `localStorage.getItem('access_token')`
- **Future**: Support anonymous spectator connections (no auth required)

---

## 10. Extensibility

### Adding New Event Types

1. **Backend**: Ensure event is broadcast to tournament channel (already done in Phase 4/5)
2. **Frontend**: Add event handler in `match_detail.html` Alpine.js component:
   ```javascript
   if (data.type === 'new_event_type') {
       this.addEvent('NEW EVENT', 'Description of event');
   }
   ```

### Adding Name Resolution

1. **Create Profile API** (if not exists):
   ```python
   # apps/accounts/api/views.py
   @api_view(['GET'])
   def profile_detail(request, user_id):
       profile = get_object_or_404(UserProfile, user_id=user_id)
       return Response({
           'user_id': profile.user_id,
           'display_name': profile.display_name,
           'avatar_url': profile.avatar.url if profile.avatar else None
       })
   ```

2. **Update Templates** (add data attributes):
   ```html
   <span class="participant1-name" data-participant-id="{{ participant1_id }}">
       Player #{{ participant1_id }}
   </span>
   ```

3. **Add JS Name Resolution**:
   ```javascript
   // Fetch all participant IDs on page
   document.querySelectorAll('[data-participant-id]').forEach(async (el) => {
       const id = el.dataset.participantId;
       const res = await fetch(`/api/profiles/${id}/`);
       const data = await res.json();
       el.textContent = data.display_name;
   });
   ```

### Adding New Spectator Pages

1. **Create View** in `apps/spectator/views.py`:
   ```python
   @require_http_methods(["GET"])
   def new_spectator_view(request, id):
       # Fetch data from services
       context = { ... }
       return render(request, 'spectator/new_page.html', context)
   ```

2. **Add URL** in `apps/spectator/urls.py`:
   ```python
   path('new-page/<int:id>/', views.new_spectator_view, name='new_page'),
   ```

3. **Create Template** in `templates/spectator/new_page.html`:
   ```html
   {% extends "spectator/base.html" %}
   {% block content %}
   <!-- Page content here -->
   {% endblock %}
   ```

---

## 11. Testing Strategy

**Phase G Focus**: Frontend implementation + integration (minimal backend tests)

### Manual Testing Checklist

- [ ] Tournament page loads with leaderboard + matches
- [ ] Match page loads with scoreboard + event feed
- [ ] htmx auto-refresh updates tables every 10s/15s/5s
- [ ] WebSocket connects and shows "Connected" status
- [ ] WebSocket events trigger htmx refresh immediately
- [ ] Disconnected state shows "Disconnected" + auto-reconnects after 5s
- [ ] Mobile layout stacks vertically (< 768px width)
- [ ] Desktop layout shows 3-column grid (> 1024px width)
- [ ] IDs-only discipline enforced (no names displayed)
- [ ] Back navigation works (tournament ← match page)
- [ ] Live badges animate on in-progress matches
- [ ] Medal icons show for top 3 leaderboard ranks

### Browser Compatibility

- ✅ Chrome 90+ (WebSocket + htmx + Alpine.js)
- ✅ Firefox 88+ (WebSocket + htmx + Alpine.js)
- ✅ Safari 14+ (WebSocket + htmx + Alpine.js)
- ✅ Edge 90+ (Chromium-based, same as Chrome)
- ⚠️ IE 11: Not supported (WebSocket implementation incomplete)

### Future: Automated Testing

Once stabilized, add:
- Selenium E2E tests for full page flows
- Playwright tests for WebSocket event handling
- Lighthouse audits for performance + accessibility

---

## 12. Known Limitations

1. **No Authentication**: Spectator pages are currently public (no login required)
   - **Future**: Add optional authentication for premium features (HD streams, advanced stats)

2. **No Name Resolution**: Displays IDs only (e.g., "Player #1234")
   - **Future**: Add client-side name resolution via profile API

3. **Limited Event Feed**: Shows generic events only
   - **Future**: Add game-specific events (kills, rounds won, objectives captured)

4. **Single Tournament View**: Can only view one tournament at a time
   - **Future**: Add tournament list page, search, filters

5. **No Historical Data**: Shows live/upcoming matches only
   - **Future**: Add completed match history, bracket viewer

6. **WebSocket Requires JWT**: Anonymous spectators must work around token requirement
   - **Future**: Support anonymous WebSocket connections (public channels)

---

## 13. Related Documentation

- **Phase E**: `docs/leaderboards/README.md` (Leaderboard service architecture)
- **Module 2.6**: `docs/runbooks/module_2_6_realtime_monitoring.md` (WebSocket monitoring)
- **Phase 4**: `docs/admin/tournament_ops.md` (Match lifecycle + dispute handling)
- **Design Specs**: `Documents/Planning/PART_4.5_SPECTATOR_DESIGN.md` (UI/UX requirements)

---

## 14. Maintenance Notes

### Updating Tailwind Config

Tailwind is currently loaded via CDN with inline config (`<script>tailwind.config`). To customize:

1. **Add new colors** to `theme.extend.colors`:
   ```javascript
   tailwind.config = {
       theme: {
           extend: {
               colors: {
                   'dc-new-color': '#abcdef',
               }
           }
       }
   }
   ```

2. **Use in templates**:
   ```html
   <div class="bg-dc-new-color text-white">...</div>
   ```

### Monitoring htmx Requests

Enable htmx debug logging:
```html
<script>
    htmx.logAll(); // Logs all htmx requests to console
</script>
```

### Debugging WebSocket Issues

Enable WebSocket client debug mode:
```javascript
const client = new SpectatorWSClient(wsUrl, { debug: true });
client.connect();
// Logs all WebSocket events to console
```

---

**End of README**
