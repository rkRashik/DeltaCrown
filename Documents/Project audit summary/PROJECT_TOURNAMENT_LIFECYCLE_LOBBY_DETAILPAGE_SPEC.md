# Tournament Lifecycle, Lobby Room & Detail Page Data Model (Backend)

**Document Type:** Backend Architecture Specification - Part 2  
**Last Updated:** November 20, 2025  
**Related:** `PROJECT_TOURNAMENT_BACKEND_SPEC.md` (Part 1)  
**Purpose:** Document tournament state machine, lobby functionality, and detail page data availability

---

## 1. Tournament Lifecycle & States

### 1.1 Status Enum & State Machine

**Source:** `apps/tournaments/models/tournament.py` (lines 145-169)

```python
class Tournament(models.Model):
    # Status choices (follows state machine from planning docs)
    DRAFT = 'draft'
    PENDING_APPROVAL = 'pending_approval'
    PUBLISHED = 'published'
    REGISTRATION_OPEN = 'registration_open'
    REGISTRATION_CLOSED = 'registration_closed'
    LIVE = 'live'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    ARCHIVED = 'archived'
    
    STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (PENDING_APPROVAL, 'Pending Approval'),
        (PUBLISHED, 'Published'),
        (REGISTRATION_OPEN, 'Registration Open'),
        (REGISTRATION_CLOSED, 'Registration Closed'),
        (LIVE, 'Live'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
        (ARCHIVED, 'Archived'),
    ]
    
    status = CharField(max_length=30, choices=STATUS_CHOICES, default=DRAFT, db_index=True)
```

### 1.2 State Definitions & Meaning

| Status | Internal Value | Logical Meaning | Visibility | Actions Allowed |
|--------|----------------|-----------------|------------|-----------------|
| **Draft** | `draft` | Tournament being configured by organizer | Organizer only | Edit all fields, add custom fields, preview |
| **Pending Approval** | `pending_approval` | Submitted for admin review (for community tournaments) | Organizer + admins | View only, admins can approve/reject |
| **Published** | `published` | Tournament visible to public, registration not yet open | Public | View details, set reminders, share |
| **Registration Open** | `registration_open` | Registration window is active | Public | Register, view roster, share |
| **Registration Closed** | `registration_closed` | Registration ended, tournament not yet started | Public + participants | View roster, check brackets, check in (if window open) |
| **Live** | `live` | Tournament in progress, matches being played | Public + participants | Watch matches, view brackets, spectate streams |
| **Completed** | `completed` | Tournament finished with winners determined | Public | View results, download certificates, see replays |
| **Cancelled** | `cancelled` | Tournament was cancelled by organizer/admin | Public (historical) | View reason, process refunds |
| **Archived** | `archived` | Historical tournament, moved to archive | Search only | Read-only access |

### 1.3 State Machine Transitions

**Linear progression path (normal flow):**
```
draft → pending_approval → published → registration_open → registration_closed → live → completed → archived
```

**Shortcuts and exceptions:**
- `draft` → `published` (skip approval if organizer is admin or tournament is official)
- `draft` → `cancelled` (organizer cancels before publishing)
- `published` → `cancelled` (organizer/admin cancels before registration)
- `registration_open` → `cancelled` (cancellation with refunds)
- `registration_closed` → `cancelled` (cancellation after registration closes)
- `live` → `cancelled` (mid-tournament cancellation)
- Any status → `archived` (manual archival by admins)

**Business rule enforcement:**
- Cannot transition back to earlier states (one-way progression)
- `registration_open` → `registration_closed` happens automatically when `registration_end` timestamp passes
- `registration_closed` → `live` happens automatically when `tournament_start` timestamp passes (if min participants met)
- `live` → `completed` happens automatically when all matches complete and winner determined

### 1.4 Helper Methods & Properties

**Source:** `apps/tournaments/models/tournament.py` (lines 541-566)

#### Tournament.is_registration_open() → bool
```python
def is_registration_open(self) -> bool:
    """
    Check if registration is currently open.
    
    Returns:
        True if registration is open and within the time window
    """
    now = timezone.now()
    return (
        self.status == self.REGISTRATION_OPEN
        and self.registration_start <= now <= self.registration_end
    )
```

**Usage:** Used to determine CTA button state on detail page

#### Tournament.spots_remaining() → int
```python
def spots_remaining(self) -> int:
    """
    Calculate number of spots remaining.
    
    Returns:
        Number of available spots (0 if full or over-subscribed)
    """
    return max(0, self.max_participants - self.total_registrations)
```

**Usage:** Display "X slots left" on tournament cards

#### Tournament.is_full() → bool
```python
def is_full(self) -> bool:
    """Check if tournament has reached capacity."""
    return self.total_registrations >= self.max_participants
```

**Usage:** Disable registration, show "Full" badge

**Additional computed properties (not explicit methods, inferred from views):**
- **is_live:** `status == LIVE`
- **is_completed:** `status == COMPLETED`
- **is_upcoming:** `status in [PUBLISHED, REGISTRATION_OPEN, REGISTRATION_CLOSED] and tournament_start > now`
- **is_past:** `status in [COMPLETED, ARCHIVED] or tournament_end < now`

### 1.5 Time-Based Logic & Automatic Transitions

**Source:** Inferred from field definitions and planning documents

#### Registration Window
```python
# Model fields
registration_start = DateTimeField(help_text='When registration opens')
registration_end = DateTimeField(help_text='When registration closes')
```

**Automatic transition logic (expected to be in Celery periodic task):**
```python
# When registration_start is reached:
if tournament.status == PUBLISHED and now >= tournament.registration_start:
    tournament.status = REGISTRATION_OPEN
    tournament.save()

# When registration_end is reached:
if tournament.status == REGISTRATION_OPEN and now >= tournament.registration_end:
    tournament.status = REGISTRATION_CLOSED
    tournament.save()
```

#### Tournament Start
```python
# Model field
tournament_start = DateTimeField(help_text='When tournament begins')
```

**Automatic transition logic:**
```python
# When tournament_start is reached:
if tournament.status == REGISTRATION_CLOSED and now >= tournament.tournament_start:
    if tournament.total_registrations >= tournament.min_participants:
        tournament.status = LIVE
        tournament.save()
        # Trigger bracket generation if not already done
```

#### Check-In Window
```python
# Model fields
enable_check_in = BooleanField(default=True)
check_in_minutes_before = PositiveIntegerField(default=15)  # 15 minutes default
check_in_closes_minutes_before = PositiveIntegerField(default=10)  # Closes 10 min before start
```

**Check-in window calculation:**
```python
check_in_opens_at = tournament.tournament_start - timedelta(minutes=check_in_minutes_before)
check_in_closes_at = tournament.tournament_start - timedelta(minutes=check_in_closes_minutes_before)

# Window is open if:
check_in_open = (
    enable_check_in 
    and check_in_opens_at <= now <= check_in_closes_at
)
```

**Automatic forfeit logic (if enabled):**
```python
# When check-in window closes:
if lobby.auto_forfeit_no_show:
    # For each registration without check-in:
    for registration in tournament.registrations.filter(status=CONFIRMED, checked_in=False):
        registration.status = NO_SHOW
        registration.save()
        # Optionally remove from bracket or mark as forfeit
```

#### Tournament End
```python
# Model field
tournament_end = DateTimeField(null=True, blank=True, help_text='When tournament ends (set automatically)')
```

**Automatic transition logic:**
```python
# When all matches complete and winner determined:
if tournament.status == LIVE and all_matches_complete():
    winner = determine_winner()
    tournament.status = COMPLETED
    tournament.tournament_end = timezone.now()
    tournament.save()
    # Trigger certificate generation, prize distribution
```

### 1.6 Planned vs Implemented Transitions

**Implemented ✅:**
- Manual status changes via Django Admin
- `draft` → `published` (manual)
- `live` → `completed` (automatic when winner determined)
- All status checks in views (`is_registration_open()`, `is_full()`)

**Partially Implemented 🟡:**
- Time-based transitions (logic exists in models, Celery tasks not confirmed)
- Check-in window enforcement (models and views ready, automatic forfeit TBD)

**Planned but Not Confirmed 📋:**
- Automatic `published` → `registration_open` at `registration_start` time
- Automatic `registration_open` → `registration_closed` at `registration_end` time
- Automatic `registration_closed` → `live` at `tournament_start` time (if min participants met)
- Email notifications on each state transition
- WebSocket broadcast on state changes

---

## 2. Tournament Lobby Room – Backend Behavior

### 2.1 Purpose & User Flow

**FE-T-007:** Tournament Lobby / Participant Hub (Sprint 5 implementation - November 20, 2025)

**Source:** `apps/tournaments/views/lobby.py`, `apps/tournaments/models/lobby.py`

The lobby is a **pre-tournament hub** for registered participants, accessible after registration is confirmed and before tournament starts. It serves as:

1. **Check-in countdown center:** Shows time until check-in window opens/closes
2. **Roster visibility:** Displays all confirmed participants with check-in status
3. **Announcement board:** Organizers post real-time updates, rule changes, reminders
4. **Tournament prep:** Links to rules, brackets (if seeded), match schedule

**URL Pattern:** `/tournaments/<slug>/lobby/`

**Access Control:**
- Must be logged in
- Must have `Registration` with `status='confirmed'` for this tournament
- Redirects to detail page if not registered

### 2.2 Models

#### TournamentLobby (OneToOne → Tournament)

**Source:** `apps/tournaments/models/lobby.py` (lines 21-139)

```python
class TournamentLobby(TimestampedModel):
    """Central hub/lobby for tournament participants."""
    
    tournament = OneToOneField('Tournament', related_name='lobby')
    
    # Check-in configuration
    check_in_opens_at = DateTimeField(null=True, blank=True)
    check_in_closes_at = DateTimeField(null=True, blank=True)
    check_in_required = BooleanField(default=True)
    auto_forfeit_no_show = BooleanField(default=True)
    
    # Content
    lobby_message = TextField(blank=True)  # Welcome message
    
    # Visibility controls
    bracket_visibility = CharField(
        max_length=20,
        choices=[('hidden', 'Hidden'), ('seeded_only', 'Seeded Only'), ('full', 'Full Bracket')],
        default='seeded_only'
    )
    roster_visibility = CharField(
        max_length=20,
        choices=[('hidden', 'Hidden'), ('count_only', 'Count Only'), ('full', 'Full Roster')],
        default='full'
    )
    
    # External links
    rules_url = URLField(blank=True)
    discord_server_url = URLField(blank=True)
    
    # Config (JSONB)
    config = JSONField(default=dict, blank=True)
```

**Config JSONB structure:**
```json
{
  "announcement_refresh_seconds": 30,
  "roster_refresh_seconds": 10,
  "check_in_reminder_minutes": [60, 30, 15, 5],
  "show_seed_assignments": true,
  "show_match_schedule": false
}
```

**Helper Properties:**

```python
@property
def is_check_in_open(self) -> bool:
    """Check if check-in is currently open."""
    if not self.check_in_required:
        return False
    
    now = timezone.now()
    
    if self.check_in_opens_at and now < self.check_in_opens_at:
        return False
    
    if self.check_in_closes_at and now > self.check_in_closes_at:
        return False
    
    return True

@property
def check_in_status(self) -> str:
    """Get human-readable check-in status."""
    # Returns: 'not_required' | 'not_open' | 'closed' | 'open'
    if not self.check_in_required:
        return 'not_required'
    
    now = timezone.now()
    
    if self.check_in_opens_at and now < self.check_in_opens_at:
        return 'not_open'
    
    if self.check_in_closes_at and now > self.check_in_closes_at:
        return 'closed'
    
    return 'open'

@property
def check_in_countdown_seconds(self) -> int:
    """Get seconds until check-in closes (for countdown timer)."""
    if not self.check_in_closes_at:
        return None
    
    now = timezone.now()
    if now > self.check_in_closes_at:
        return 0
    
    delta = self.check_in_closes_at - now
    return int(delta.total_seconds())
```

#### CheckIn (per Registration)

**Source:** `apps/tournaments/models/lobby.py` (lines 216-357)

```python
class CheckIn(TimestampedModel):
    """Tracks participant check-in status."""
    
    tournament = ForeignKey('Tournament', related_name='check_ins')
    registration = OneToOneField('Registration', related_name='check_in')
    
    # Either user OR team (matches registration)
    user = ForeignKey('accounts.User', null=True, blank=True)
    team = ForeignKey('teams.Team', null=True, blank=True)
    
    # Check-in status
    is_checked_in = BooleanField(default=False)
    checked_in_at = DateTimeField(null=True, blank=True)
    checked_in_by = ForeignKey('accounts.User', null=True, blank=True, related_name='+')
    
    # Forfeit tracking
    is_forfeited = BooleanField(default=False)
    forfeited_at = DateTimeField(null=True, blank=True)
    forfeit_reason = CharField(max_length=255, blank=True)
    
    notes = TextField(blank=True)
    is_deleted = BooleanField(default=False)
```

**Key Method:**
```python
def perform_check_in(self, user):
    """Mark participant as checked in."""
    self.is_checked_in = True
    self.checked_in_at = timezone.now()
    self.checked_in_by = user
    self.save()
```

**Constraints:**
- XOR constraint: Exactly one of `user` OR `team` must be set
- Unique: One check-in per registration

#### LobbyAnnouncement

**Source:** `apps/tournaments/models/lobby.py` (lines 360-449)

```python
class LobbyAnnouncement(TimestampedModel):
    """Real-time announcements shown to participants in lobby."""
    
    lobby = ForeignKey(TournamentLobby, related_name='announcements')
    posted_by = ForeignKey('accounts.User', null=True)
    
    title = CharField(max_length=200)
    message = TextField()
    
    announcement_type = CharField(
        max_length=20,
        choices=[('info', 'Information'), ('warning', 'Warning'), ('urgent', 'Urgent'), ('success', 'Success')],
        default='info'
    )
    
    is_pinned = BooleanField(default=False)  # Pinned announcements appear at top
    display_until = DateTimeField(null=True, blank=True)  # Auto-hide after this time
    is_visible = BooleanField(default=True)
    is_deleted = BooleanField(default=False)
```

**Ordering:** `['-is_pinned', '-created_at']` (pinned first, then newest)

### 2.3 Views & Endpoints

#### TournamentLobbyView (Main Lobby Page)

**Source:** `apps/tournaments/views/lobby.py` (lines 19-82)

**URL:** `/tournaments/<slug>/lobby/`  
**Template:** `templates/tournaments/lobby/hub.html`  
**Method:** GET  
**Auth:** Login required

**Context Variables Passed to Template:**

```python
{
    'tournament': <Tournament instance>,
    'lobby': <TournamentLobby instance>,
    'check_in': <CheckIn instance for current user>,
    'roster_data': <dict from LobbyService.get_roster()>,
    'announcements': <QuerySet of LobbyAnnouncement>,
    'is_check_in_open': <bool>,
    'check_in_status': <str: 'open'|'not_open'|'closed'|'not_required'>,
    'check_in_countdown': <int seconds or None>,
}
```

**Access Control:**
```python
# Check if user is registered
is_registered = tournament.registrations.filter(
    user=request.user,
    status='confirmed',
    is_deleted=False
).exists()

if not is_registered:
    messages.warning(request, "You must be registered to access the tournament lobby")
    return redirect('tournaments:detail', slug=slug)
```

#### CheckInView (Check-In Action)

**Source:** `apps/tournaments/views/lobby.py` (lines 85-140)

**URL:** `/tournaments/<slug>/lobby/check-in/`  
**Method:** POST  
**Auth:** Login required  
**Content-Type:** `application/json` (AJAX) or form data

**Request Flow:**
1. Validate user has confirmed registration
2. Check if check-in window is open (via `lobby.is_check_in_open`)
3. Detect team_id if team tournament (via registration.team_id)
4. Call `LobbyService.perform_check_in(tournament_id, user_id, team_id)`
5. Return JSON response or redirect

**Response (JSON):**
```json
{
  "success": true,
  "message": "Check-in successful",
  "checked_in_at": "2025-11-20T14:30:00Z"
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Check-in window has closed"
}
```

#### LobbyRosterAPIView (Real-Time Roster Data)

**Source:** `apps/tournaments/views/lobby.py` (lines 143-168)

**URL:** `/api/<slug>/lobby/roster/`  
**Method:** GET  
**Auth:** Login required (must be registered participant)  
**Usage:** AJAX polling every 10 seconds for real-time roster updates

**Response:**
```json
{
  "total_participants": 32,
  "checked_in_count": 28,
  "not_checked_in_count": 4,
  "participants": [
    {
      "id": 123,
      "name": "Team Alpha",
      "type": "team",
      "checked_in": true,
      "checked_in_at": "2025-11-20T14:25:00Z",
      "seed": 1
    },
    {
      "id": 456,
      "name": "Player_Beta",
      "type": "solo",
      "checked_in": false,
      "checked_in_at": null,
      "seed": 2
    }
  ]
}
```

#### LobbyAnnouncementsAPIView (Real-Time Announcements)

**Source:** `apps/tournaments/views/lobby.py` (lines 171-212)

**URL:** `/api/<slug>/lobby/announcements/`  
**Method:** GET  
**Auth:** Login required (must be registered participant)  
**Usage:** AJAX polling every 30 seconds for new announcements

**Response:**
```json
{
  "announcements": [
    {
      "id": 789,
      "title": "Check-in opens in 15 minutes!",
      "message": "Make sure you're ready to check in when the window opens.",
      "type": "warning",
      "is_pinned": true,
      "posted_by": "organizer_username",
      "created_at": "2025-11-20T13:45:00Z"
    }
  ]
}
```

### 2.4 Service Layer

#### LobbyService

**Source:** Inferred from view imports (`apps/tournaments/services/lobby_service.py`)

**Methods:**

```python
class LobbyService:
    @staticmethod
    def get_roster(tournament_id: int) -> dict:
        """
        Get complete roster with check-in status.
        
        Returns:
            {
                'total_participants': int,
                'checked_in_count': int,
                'not_checked_in_count': int,
                'participants': List[dict]
            }
        """
    
    @staticmethod
    def get_announcements(tournament_id: int) -> QuerySet:
        """Get visible announcements ordered by pinned then created_at."""
    
    @staticmethod
    def perform_check_in(tournament_id: int, user_id: int, team_id: int = None) -> CheckIn:
        """
        Perform check-in for user/team.
        
        Validates:
        - Check-in window is open
        - User has confirmed registration
        - Not already checked in
        
        Raises:
            ValidationError if check-in not allowed
        """
```

### 2.5 WebSocket / Real-Time Updates

**Source:** `apps/tournaments/consumers.py` (lines 100-190)

**Consumer:** `TournamentBracketConsumer`  
**WebSocket URL:** `ws://domain/ws/tournament/<tournament_slug>/?token=<jwt>`

**Event Types Relevant to Lobby:**
- `registration_checked_in` (when participant checks in)
- `lobby_announcement` (new announcement posted)
- `bracket_generated` (seeding revealed, if bracket_visibility='full')

**Client-Side Usage:**
```javascript
// Connect to WebSocket for real-time updates
const ws = new WebSocket(`ws://domain/ws/tournament/${slug}/?token=${jwt_token}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'registration_checked_in') {
    // Update roster UI to show new check-in
    updateRosterCheckIn(data.registration_id);
  }
  
  if (data.type === 'lobby_announcement') {
    // Prepend new announcement to list
    prependAnnouncement(data.announcement);
  }
};
```

### 2.6 Data Exposed by Lobby

**Participant Roster:**
- Participant name (user or team)
- Participant type (solo/team)
- Check-in status (✓ checked in, ✗ not checked in)
- Check-in timestamp
- Seed assignment (if `config.show_seed_assignments=true` and seeding done)

**Check-In Countdown:**
- Opens at: `lobby.check_in_opens_at`
- Closes at: `lobby.check_in_closes_at`
- Seconds remaining: `lobby.check_in_countdown_seconds`
- Status: `lobby.check_in_status` ('not_open', 'open', 'closed', 'not_required')

**Announcements:**
- Title, message, type (info/warning/urgent/success)
- Posted by (organizer username)
- Timestamp
- Pinned status

**Upcoming Match Info:**
- First round matches (if bracket generated and visible)
- Match times (if scheduled)

**Tournament Info Links:**
- Rules PDF: `tournament.rules_pdf`
- Discord server: `lobby.discord_server_url`
- Stream URLs: `tournament.stream_youtube_url`, `tournament.stream_twitch_url`

**Standings:**
- Not typically shown in lobby (pre-tournament state)
- Only shown if tournament has previous rounds and is using group stage format

---

## 3. Data Model for Tournament Detail Page (Backend-Driven)

### 3.1 View Definition

**Source:** `apps/tournaments/views/main.py` (lines 140-431)

**View Class:** `TournamentDetailView(DetailView)`  
**URL Pattern:** `/tournaments/<slug>/`  
**Template:** `templates/tournaments/detail.html`  
**Method:** GET  
**Auth:** Optional (anonymous users see generic CTA, logged-in users see personalized CTA)

**QuerySet Optimization:**
```python
queryset = Tournament.objects.select_related('game', 'organizer').filter(
    status__in=['published', 'registration_open', 'live', 'completed']
)
```

### 3.2 Context Data Structure

**Source:** `TournamentDetailView.get_context_data()` (lines 180-425)

```python
context = {
    'tournament': <Tournament instance>,
    
    # FE-T-003: Registration CTA state
    'cta_state': <str>,
    'cta_label': <str>,
    'cta_disabled': <bool>,
    'cta_reason': <str>,
    'is_registered': <bool>,
    'can_register': <bool>,
    'registration_status': <dict or None>,
    
    # Capacity/slots
    'slots_filled': <int>,
    'slots_total': <int>,
    'slots_percentage': <float>,
    
    # Announcements
    'announcements': <QuerySet[TournamentAnnouncement]>,
}
```

### 3.3 Hero & Meta Strip Data

**Available from Tournament model:**

```python
# Identity
tournament.name                    # "eFootball 3K Thunder League"
tournament.slug                    # "efootball-3k-thunder-league"
tournament.description             # Markdown/text description

# Game info
tournament.game                    # ForeignKey → Game instance
tournament.game.name               # "eFootball 2024"
tournament.game.slug               # "efootball"
tournament.game.icon               # ImageField URL
tournament.game.default_team_size  # 5

# Visual assets
tournament.banner_image            # ImageField → /media/tournaments/banners/xxx.jpg
tournament.thumbnail_image         # ImageField → /media/tournaments/thumbnails/xxx.jpg
tournament.promo_video_url         # YouTube/Vimeo URL

# Status & lifecycle
tournament.status                  # 'registration_open' | 'live' | 'completed' etc.
tournament.get_status_display()    # Human-readable: "Registration Open"
tournament.published_at            # DateTimeField

# Dates
tournament.registration_start      # DateTimeField
tournament.registration_end        # DateTimeField
tournament.tournament_start        # DateTimeField
tournament.tournament_end          # DateTimeField (set when completed)

# Capacity
tournament.max_participants        # int (e.g., 32)
tournament.min_participants        # int (e.g., 8)
tournament.total_registrations     # Denormalized count
context['slots_filled']            # Calculated: confirmed registrations count
context['slots_total']             # tournament.max_participants
context['slots_percentage']        # (slots_filled / slots_total) * 100

# Entry fee
tournament.has_entry_fee           # bool
tournament.entry_fee_amount        # Decimal (e.g., 500.00)
tournament.entry_fee_currency      # str (e.g., 'BDT')
tournament.entry_fee_deltacoin     # int (e.g., 1000)
tournament.payment_methods         # ArrayField(['bkash', 'nagad', 'deltacoin'])

# Fee waiver logic
tournament.enable_fee_waiver       # bool
tournament.fee_waiver_top_n_teams  # int (e.g., 8)
# To check if user's team is in top N:
from apps.teams.models import TeamRankingBreakdown
user_team = get_users_team_for_game(user, tournament.game)
ranking = TeamRankingBreakdown.objects.get(team=user_team)
top_teams = get_top_n_teams(tournament.game, tournament.fee_waiver_top_n_teams)
is_fee_waived = user_team in top_teams

# Organizer
tournament.organizer               # ForeignKey → User
tournament.organizer.username      # str
tournament.organizer.profile.avatar # ImageField
tournament.is_official             # bool (DeltaCrown official tournament)

# SEO
tournament.meta_description        # TextField
tournament.meta_keywords           # ArrayField[str]
```

### 3.4 Rules

**Available fields:**

```python
# Text rules
tournament.rules_text              # TextField (Markdown supported)

# PDF rules
tournament.rules_pdf               # FileField → /media/tournaments/rules/xxx.pdf
tournament.rules_pdf.url           # URL to PDF (if exists)

# External rules link
# (from TournamentLobby if exists)
tournament.lobby.rules_url         # URLField (external Google Docs, Notion, etc.)

# Terms & Conditions (NEW)
tournament.terms_and_conditions    # TextField
tournament.terms_pdf               # FileField
tournament.require_terms_acceptance # bool (must check box during registration)
```

**Display logic:**
```python
# Priority order:
if tournament.rules_pdf:
    # Show PDF viewer or download button
elif tournament.lobby and tournament.lobby.rules_url:
    # Show external link
elif tournament.rules_text:
    # Render Markdown text
else:
    # Show "Rules will be announced soon"
```

### 3.5 Prizes

**Available fields:**

```python
# Total prize pool
tournament.prize_pool              # Decimal (e.g., 50000.00)
tournament.prize_currency          # str (e.g., 'BDT')
tournament.prize_deltacoin         # int (e.g., 10000)

# Prize breakdown (JSONB)
tournament.prize_distribution      # JSONField
```

**Prize distribution structure:**
```json
{
  "1": {"percentage": "50%", "amount": 25000, "deltacoin": 5000},
  "2": {"percentage": "30%", "amount": 15000, "deltacoin": 3000},
  "3": {"percentage": "20%", "amount": 10000, "deltacoin": 2000}
}
```

**Helper to get structured breakdown:**
```python
def get_prize_breakdown(tournament):
    """Returns list of placement prizes with calculated amounts."""
    breakdown = []
    
    for place, data in tournament.prize_distribution.items():
        if isinstance(data, dict):
            breakdown.append({
                'placement': int(place),
                'percentage': data.get('percentage', ''),
                'amount_bdt': data.get('amount', 0),
                'deltacoin': data.get('deltacoin', 0)
            })
        else:
            # Legacy format: just percentage string
            breakdown.append({
                'placement': int(place),
                'percentage': data,
                'amount_bdt': calculate_from_percentage(tournament.prize_pool, data),
                'deltacoin': 0
            })
    
    return sorted(breakdown, key=lambda x: x['placement'])
```

### 3.6 Participants & Teams

**Querying registered participants:**

```python
from apps.tournaments.models import Registration

# Get all confirmed registrations
registrations = tournament.registrations.filter(
    status='confirmed',
    is_deleted=False
).select_related('user', 'user__profile')

# For team tournaments
team_registrations = tournament.registrations.filter(
    status='confirmed',
    is_deleted=False,
    team_id__isnull=False
)

# Access team data via team_id (IntegerField reference)
for reg in team_registrations:
    team = Team.objects.get(id=reg.team_id)
    print(team.name, team.tag, team.logo, team.ranking)
```

**Team fields available:**

```python
# From apps.teams.models import Team
team.name                          # str (e.g., "Team DeltaCrown")
team.tag                           # str (e.g., "DC")
team.display_name                  # property: "Team DeltaCrown (DC)"
team.logo                          # ImageField
team.banner                        # ImageField
team.slug                          # str

# Ranking info (from TeamRankingBreakdown)
ranking = TeamRankingBreakdown.objects.get(team=team, game=tournament.game.slug)
ranking.final_total                # int (total ranking points)
ranking.tournament_winner_points   # int
ranking.tournament_runner_up_points # int
ranking.tournament_participation_points # int
ranking.manual_adjustment_points   # int
```

**Fee waiver eligibility check:**

```python
def check_fee_waiver_eligibility(user, tournament):
    """Check if user's team is eligible for fee waiver."""
    if not tournament.enable_fee_waiver:
        return False
    
    # Get user's team for this game
    team = get_users_team_for_game(user, tournament.game)
    if not team:
        return False
    
    # Get top N teams by ranking
    top_teams = TeamRankingBreakdown.objects.filter(
        game=tournament.game.slug
    ).order_by('-final_total')[:tournament.fee_waiver_top_n_teams]
    
    top_team_ids = [r.team_id for r in top_teams]
    
    return team.id in top_team_ids
```

### 3.7 Brackets, Rounds & Matches

**Bracket model access:**

```python
# Check if bracket exists
if hasattr(tournament, 'bracket'):
    bracket = tournament.bracket
    
    # Bracket metadata
    bracket.format                 # 'single_elimination' | 'double_elimination' | etc.
    bracket.seeding_method         # 'slot-order' | 'random' | 'manual' | 'ranked'
    bracket.total_rounds           # int (calculated from participant count)
    bracket.is_finalized           # bool (prevents regeneration)
    bracket.bracket_structure      # JSONB with full bracket tree (GIN indexed)
```

**Querying matches:**

```python
from apps.tournaments.models import Match

# All matches for tournament
matches = Match.objects.filter(
    tournament=tournament,
    is_deleted=False
).order_by('round_number', 'match_number')

# Upcoming matches
upcoming = Match.objects.filter(
    tournament=tournament,
    state__in=['scheduled', 'check_in', 'ready'],
    is_deleted=False
).order_by('scheduled_time')

# Live matches
live = Match.objects.filter(
    tournament=tournament,
    state='live',
    is_deleted=False
)

# Completed matches
completed = Match.objects.filter(
    tournament=tournament,
    state='completed',
    is_deleted=False
).order_by('-completed_at')

# Matches for specific team/user
team_matches = Match.objects.filter(
    tournament=tournament,
    is_deleted=False
).filter(
    Q(participant1_id=team_id) | Q(participant2_id=team_id)
)
```

**Match fields available:**

```python
match.id                           # int
match.round_number                 # int (1 = first round)
match.match_number                 # int (position within round)
match.state                        # 'scheduled' | 'check_in' | 'ready' | 'live' | 'pending_result' | 'completed' | 'disputed' | 'forfeit' | 'cancelled'

# Participants
match.participant1_id              # IntegerField (team_id or registration_id)
match.participant1_name            # CharField (cached display name)
match.participant2_id              # IntegerField
match.participant2_name            # CharField

# Scores
match.participant1_score           # int
match.participant2_score           # int
match.winner_id                    # IntegerField (participant who won)
match.loser_id                     # IntegerField

# Timing
match.scheduled_time               # DateTimeField
match.started_at                   # DateTimeField
match.completed_at                 # DateTimeField

# Check-in
match.participant1_checked_in      # bool
match.participant2_checked_in      # bool
match.check_in_deadline            # DateTimeField

# Lobby info (JSONB)
match.lobby_info                   # JSONField
# Example: {"map": "Dust 2", "server": "EU-1", "lobby_code": "ABC123", "password": "xyz"}

# Streaming
match.stream_url                   # URLField
```

### 3.8 Standings & Results

**TournamentResult model:**

```python
from apps.tournaments.models import TournamentResult

# Get result (only exists after tournament completes)
try:
    result = TournamentResult.objects.get(tournament=tournament)
    
    # Placements
    result.winner                  # ForeignKey → Registration (1st place)
    result.runner_up               # ForeignKey → Registration (2nd place)
    result.third_place             # ForeignKey → Registration (3rd place)
    
    # Determination method
    result.determination_method    # 'normal' | 'tiebreaker' | 'forfeit_chain' | 'manual'
    result.rules_applied           # JSONB (ordered list of tiebreaker rules used)
    result.requires_review         # bool (flagged for manual review if >50% forfeit)
    
    # Manual override
    result.is_override             # bool
    result.override_reason         # TextField
    result.override_actor          # ForeignKey → User
    result.override_timestamp      # DateTimeField
    
except TournamentResult.DoesNotExist:
    # Tournament not yet completed or winner not determined
    pass
```

**Accessing winner information:**

```python
if result:
    winner_registration = result.winner
    
    # For solo tournaments
    if winner_registration.user:
        winner_name = winner_registration.user.username
        winner_avatar = winner_registration.user.profile.avatar
    
    # For team tournaments
    if winner_registration.team_id:
        winner_team = Team.objects.get(id=winner_registration.team_id)
        winner_name = winner_team.display_name
        winner_logo = winner_team.logo
```

**Leaderboard/Standings during tournament:**

For tournaments with group stage or round robin format, standings are calculated from match results:

```python
# Get all completed matches
completed_matches = Match.objects.filter(
    tournament=tournament,
    state='completed',
    is_deleted=False
)

# Build standings dict
standings = {}
for match in completed_matches:
    # Award points based on match result
    # Update win/loss/draw counts
    # Sort by points, then tiebreakers
```

### 3.9 Streaming & External Links

**Available fields:**

```python
# Official streams
tournament.stream_youtube_url      # URLField (e.g., https://youtube.com/live/xyz)
tournament.stream_twitch_url       # URLField (e.g., https://twitch.tv/deltacrown)

# Promo video
tournament.promo_video_url         # URLField (YouTube/Vimeo embed)

# External links (from TournamentLobby)
if hasattr(tournament, 'lobby'):
    tournament.lobby.discord_server_url  # URLField
    tournament.lobby.rules_url           # URLField (external rules doc)

# SEO/Social sharing
tournament.meta_description        # TextField (for Open Graph)
# Social share preview image: tournament.banner_image or tournament.thumbnail_image
```

### 3.10 Feature Toggles

**Source:** `apps/tournaments/models/tournament.py` (lines 371-407)

All feature toggles are boolean fields that enable/disable specific tournament behaviors:

```python
# Check-in requirements
tournament.enable_check_in         # bool (default: True)
tournament.check_in_minutes_before # int (default: 15) - check-in window duration
tournament.check_in_closes_minutes_before # int (default: 10)

# Seeding method
tournament.enable_dynamic_seeding  # bool (default: False)
# If True: Use team rankings from TeamRankingBreakdown for seeding
# If False: Use registration order (slot_number) for seeding

# Real-time features
tournament.enable_live_updates     # bool (default: True)
# Controls WebSocket broadcasting for match updates

# Post-tournament features
tournament.enable_certificates     # bool (default: True)
# If True: Generate PDF/PNG certificates for winners

# Interactive features (planned, not fully implemented)
tournament.enable_challenges       # bool (default: False)
# Planned: Bonus challenges during tournament (e.g., "First Blood", "Ace Round")

tournament.enable_fan_voting       # bool (default: False)
# Planned: Spectator voting/predictions for match outcomes
```

**Usage in views:**

```python
# Check if feature is enabled before showing UI
if tournament.enable_check_in:
    # Show check-in countdown and button
    pass

if tournament.enable_dynamic_seeding:
    # Use TournamentRankingService for seeding
    participants = TournamentRankingService.get_ranked_participants(tournament)
else:
    # Use registration order
    participants = tournament.registrations.filter(status='confirmed').order_by('slot_number')

if tournament.enable_certificates:
    # Show "Download Certificate" button on results page
    pass
```

### 3.11 Registration CTA States (FE-T-003)

**Source:** `apps/tournaments/views/main.py` (lines 210-385)

The detail page dynamically determines the Call-To-Action button state based on:
- User authentication status
- Tournament status
- Registration eligibility
- Payment status
- Check-in requirements

**All possible CTA states:**

| State | Label | Disabled | When Shown | Action |
|-------|-------|----------|------------|--------|
| `login_required` | "Login to Register" | False | User not authenticated | Redirect to login |
| `open` | "Register Now" | False | Registration open, user eligible | Go to registration form |
| `closed` | "Registration Closed" | True | Registration window ended | None |
| `full` | "Tournament Full" | True | Max participants reached | None |
| `upcoming` | "Coming Soon" | True | Published but registration not yet open | None |
| `registered` | "You're Registered" | False | User registered, payment confirmed | View registration details |
| `payment_pending` | "Payment Required" | False | Registered but payment not submitted | Go to payment submission |
| `approval_pending` | "Awaiting Approval" | True | Payment submitted, waiting for organizer verification | None |
| `check_in_required` | "Check-In Required" | False | Check-in window open, not checked in | Go to check-in |
| `checked_in` | "You're Checked In ✓" | True | Successfully checked in | View lobby |
| `not_eligible` | "Not Eligible" | True | Failed eligibility check (generic) | None |
| `no_team_permission` | "No Permission" | True | Team tournament but user not captain | None |

**Eligibility check logic:**

```python
from apps.tournaments.services.registration_service import RegistrationService

try:
    RegistrationService.check_eligibility(
        tournament=tournament,
        user=user,
        team_id=selected_team_id
    )
    # Eligibility passed → CTA state = 'open'
except ValidationError as e:
    # Eligibility failed → Parse error message to determine state
    error_message = str(e)
    
    if 'full' in error_message.lower():
        cta_state = 'full'
    elif 'closed' in error_message.lower():
        cta_state = 'closed'
    elif 'permission' in error_message.lower():
        cta_state = 'no_team_permission'
    # etc.
```

### 3.12 Context Summary (Complete List)

**All context variables available in `detail.html` template:**

```python
{
    # Core tournament data
    'tournament': <Tournament instance with all fields>,
    
    # Registration CTA (FE-T-003)
    'cta_state': <str: one of 11 states>,
    'cta_label': <str: button text>,
    'cta_disabled': <bool>,
    'cta_reason': <str: tooltip/explanation>,
    'is_registered': <bool>,
    'can_register': <bool>,
    'registration_status': <dict or None: {'state': str, 'reason': str, 'check_in_window': dict}>,
    
    # Capacity tracking
    'slots_filled': <int: confirmed registrations count>,
    'slots_total': <int: tournament.max_participants>,
    'slots_percentage': <float: 0-100>,
    
    # Announcements
    'announcements': <QuerySet[TournamentAnnouncement]: pinned + recent>,
}
```

---

## 4. Backend Execution Plans – Cross-Check with Lifecycle & Lobby

### 4.1 Planned Features (from MAP.md)

**Source:** `Documents/ExecutionPlan/Core/MAP.md` (lines 1-3002)

#### Phase 3: Registration & Check-in

**Module 3.1: Registration API (✅ COMPLETE)**
- Status: Implemented (14 tests, eligibility validation)
- Features:
  - POST `/api/tournaments/registrations/` (create registration)
  - Eligibility checks: capacity, registration window, participation type, team permissions
  - XOR constraint: user OR team_id
  - JSONB storage: registration_data with game IDs, contact info, custom fields

**Module 3.2: Payment Verification (✅ COMPLETE)**
- Status: Implemented (29 tests, multipart upload, organizer approval)
- Features:
  - POST `/api/tournaments/payments/{id}/submit-proof/` (upload screenshot/receipt)
  - POST `/api/tournaments/payments/{id}/verify/` (organizer review)
  - Payment status workflow: pending → submitted → verified/rejected/refunded
  - File validation: max 5MB, JPG/PNG/PDF

**Module 3.3: Team Management (✅ COMPLETE)**
- Status: Implemented (27 tests)
- Features:
  - Team roster management (invite/accept/remove/transfer/disband)
  - Captain permissions for tournament registration
  - Fee waiver for top N ranked teams

**Module 3.4: Check-in System (✅ COMPLETE)**
- Status: Implemented (36 tests, 30-min window, team captain check-in)
- Features:
  - POST `/tournaments/<slug>/check-in/` (participant self check-in)
  - POST `/tournaments/<slug>/lobby/check-in/` (lobby check-in action)
  - Check-in window: opens 15 min before start, closes 10 min before start
  - Auto-forfeit for no-shows (configurable)
  - Team captain can check in entire team

#### Phase 4: Tournament Live Operations

**Module 4.1: Bracket Generation (✅ COMPLETE)**
- Status: Implemented (4 seeding strategies, bye handling, 24 tests)
- Features:
  - POST `/api/tournaments/brackets/<tournament_id>/generate/`
  - Seeding methods: slot-order, random, manual, ranked
  - Formats: single-elimination (complete), double-elimination (stub), round-robin (stub), swiss (stub)

**Module 4.2: Ranking & Seeding (✅ COMPLETE)**
- Status: Implemented (deterministic tie-breaking, 42 tests)
- Features:
  - `TournamentRankingService.get_ranked_participants()`
  - Uses `TeamRankingBreakdown.final_total` as primary sort key
  - Tie-breaking: team age DESC, team ID ASC

**Module 4.3: Match Management (✅ COMPLETE)**
- Status: Implemented (7 API endpoints, scheduling, 25 tests)
- Features:
  - Match lifecycle: scheduled → check_in → ready → live → pending_result → completed
  - 9 match states with transition validation
  - lobby_info JSONB for match lobby details (map, server, lobby code, password)

**Module 4.5: WebSocket Enhancements (✅ COMPLETE)**
- Status: Implemented (match-specific channels, heartbeat, 18 tests)
- Features:
  - `TournamentBracketConsumer` (WebSocket consumer)
  - Event types: match_started, score_updated, match_completed, bracket_updated, registration_checked_in
  - JWT authentication via query param
  - Redis channel layers for broadcasting

#### Phase 5: Tournament Post-Game

**Module 5.1: Winner Determination (✅ COMPLETE)**
- Status: Implemented (5-step tiebreaker, 14 tests, 81% coverage)
- Features:
  - `WinnerDeterminationService.determine_winner()`
  - Tiebreaker cascade: head_to_head → score_diff → seed → completion_time → manual_review
  - TournamentResult model with placements (winner, runner_up, third_place)

**Module 5.3: Certificates (✅ COMPLETE)**
- Status: Implemented (PDF/PNG, QR codes, tamper detection, 35 tests)
- Features:
  - POST `/api/tournaments/certificates/{id}/` (generate certificate)
  - GET `/api/tournaments/certificates/verify/<uuid>/` (public verification)
  - PDF: ReportLab A4 landscape
  - PNG: Pillow 1920x1080
  - SHA-256 hash for tamper detection

**Module 5.4: Analytics & Reports (✅ COMPLETE)**
- Status: Implemented (25 metrics, CSV export, 37 tests)
- Features:
  - Materialized view: `analytics_tournament_organizer_mv` (70.5× speedup)
  - Metrics: total tournaments, revenue, participants, match completion rate, etc.

**Module 5.5: Notifications & Webhooks (✅ COMPLETE)**
- Status: Implemented (HMAC-SHA256, retry logic, 43 tests)
- Features:
  - NotificationService with 20+ event types
  - WebhookService with exponential backoff (3 retries)
  - Multi-channel: in-app, email (future), webhook

### 4.2 Planned vs Implemented (Tournament Lifecycle)

| Feature | Status | Notes |
|---------|--------|-------|
| **State Machine** | ✅ Implemented | 9 states defined, transitions validated |
| **Time-Based Transitions** | 🟡 Partial | Logic exists in models, Celery tasks not confirmed |
| **Auto: published → registration_open** | 📋 Planned | Celery periodic task needed |
| **Auto: registration_open → registration_closed** | 📋 Planned | Celery periodic task needed |
| **Auto: registration_closed → live** | 📋 Planned | Celery periodic task needed (with min participants check) |
| **Auto: live → completed** | ✅ Implemented | Triggered by `WinnerDeterminationService.determine_winner()` |
| **Helper Methods** | ✅ Implemented | `is_registration_open()`, `spots_remaining()`, `is_full()` |
| **WebSocket Broadcasts on State Change** | 📋 Planned | Not confirmed |
| **Email Notifications on State Change** | 📋 Planned | NotificationService exists, integration TBD |

### 4.3 Planned vs Implemented (Tournament Lobby)

| Feature | Status | Notes |
|---------|--------|-------|
| **TournamentLobby Model** | ✅ Implemented | Full model with check-in config, visibility controls |
| **CheckIn Model** | ✅ Implemented | Full model with forfeit tracking |
| **LobbyAnnouncement Model** | ✅ Implemented | Full model with pinning, expiry |
| **Lobby Hub View** | ✅ Implemented | `/tournaments/<slug>/lobby/` with context |
| **Check-In Action Endpoint** | ✅ Implemented | POST `/tournaments/<slug>/lobby/check-in/` |
| **Roster API (AJAX)** | ✅ Implemented | GET `/api/<slug>/lobby/roster/` |
| **Announcements API (AJAX)** | ✅ Implemented | GET `/api/<slug>/lobby/announcements/` |
| **LobbyService** | ✅ Implemented | `get_roster()`, `get_announcements()`, `perform_check_in()` |
| **WebSocket Real-Time Updates** | ✅ Implemented | `registration_checked_in` event broadcast |
| **Auto-Forfeit No-Shows** | 🟡 Partial | Model flag exists, Celery task TBD |
| **Check-In Reminders** | 📋 Planned | `config.check_in_reminder_minutes` defined, notifications TBD |
| **Lobby Template** | 📋 Planned | `templates/tournaments/lobby/hub.html` (Sprint 5 frontend) |

### 4.4 Planned vs Implemented (Tournament Detail Page)

| Feature | Status | Notes |
|---------|--------|-------|
| **TournamentDetailView** | ✅ Implemented | Full view with CTA state logic |
| **Hero Section Data** | ✅ Implemented | All fields available: banner, game, status, dates, slots |
| **Rules Display** | ✅ Implemented | rules_text, rules_pdf, terms_and_conditions |
| **Prizes Display** | ✅ Implemented | prize_pool, prize_distribution JSONB |
| **Participants/Teams Query** | ✅ Implemented | Registration model with team_id references |
| **Fee Waiver Check** | ✅ Implemented | `enable_fee_waiver`, `fee_waiver_top_n_teams`, TeamRankingBreakdown integration |
| **Brackets/Matches Query** | ✅ Implemented | Full Match model with 9 states, lobby_info JSONB |
| **Standings/Results** | ✅ Implemented | TournamentResult model with placements, tiebreaker rules |
| **Streaming Links** | ✅ Implemented | stream_youtube_url, stream_twitch_url |
| **Feature Toggles** | ✅ Implemented | 11 boolean flags for features |
| **Registration CTA States** | ✅ Implemented | 11 states with eligibility checking via RegistrationService |
| **Announcements Display** | ✅ Implemented | TournamentAnnouncement model (separate from LobbyAnnouncement) |
| **Detail Page Template** | ✅ Implemented | `templates/tournaments/detail.html` (Sprint 1 frontend) |
| **Tabs (Overview, Schedule, Prizes, Rules)** | 🟡 Partial | Template structure exists, frontend polish TBD |

### 4.5 Known Gaps & Future Work

**High Priority (Needed for Production):**
1. Celery periodic tasks for time-based state transitions
2. Auto-forfeit implementation (Celery task when check-in window closes)
3. Check-in reminder notifications (email/push)
4. WebSocket broadcast on tournament state changes
5. Waitlist management (Module 3.4 deferred)

**Medium Priority (Enhances UX):**
1. Double elimination bracket algorithm (NotImplementedError stub)
2. Round robin and Swiss format implementations
3. Group stage + playoff format implementation
4. Dynamic seeding real-time updates (flag exists, not wired)
5. Fan voting system (flag exists, no implementation)
6. Challenges system (flag exists, no implementation)

**Low Priority (Nice-to-Have):**
1. Live chat in lobby
2. Prediction system for spectators
3. Match replay embedding
4. Social share cards with OG tags
5. PWA offline support for schedules

---

**End of Part 2: Tournament Lifecycle, Lobby Room & Detail Page Data Model**

**Document Status:** Complete  
**Total Sections:** 4 major sections  
**Total Lines:** ~1,400 lines  
**Coverage:** Comprehensive lifecycle, lobby, and detail page backend documentation

**Next Part (If Needed):** Part 3 could cover API endpoints, serializers, and frontend integration patterns.
