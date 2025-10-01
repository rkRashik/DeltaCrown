# Non-Captain Approval Workflow - Complete Implementation

## Overview
Implemented a complete non-captain approval system where team members can request their captain to register the team for tournaments. This provides a smooth, modern UX that prevents frustration for non-captain team members.

## Architecture

### 1. Database Model: RegistrationRequest
**File**: `apps/tournaments/models/registration_request.py`

```python
class RegistrationRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        EXPIRED = 'expired', 'Expired'
    
    requester: UserProfile  # Team member requesting approval
    captain: UserProfile    # Team captain who must approve
    tournament: Tournament  # Tournament to register for
    team: Team             # Team to register
    status: Status         # Request status
    message: TextField     # Optional message to captain
    response_message: TextField  # Captain's response
```

**Key Features**:
- Unique constraint: One pending request per requester/team/tournament combination
- Automatic expiry checking (7 days)
- `approve()` and `reject()` methods for captain actions

**Migration**: `apps/tournaments/migrations/0030_registration_request.py` ✅ Applied

### 2. Service Layer: Registration Request Management
**File**: `apps/tournaments/services/registration_request.py`

**Functions**:

#### `create_registration_request(requester, tournament, team, message="")`
- Creates a new registration request
- Validates no existing pending request
- Sends email notification to captain
- Returns the created RegistrationRequest

#### `send_captain_notification_email(request)`
- Notifies captain of new registration request
- Includes approval/rejection links
- Provides requester details and message

#### `send_requester_response_email(request, approved)`
- Notifies requester of captain's decision
- Different messages for approval vs rejection
- Includes next steps

### 3. View Logic: Request Handling
**Files**: 
- `apps/tournaments/views/registration_unified.py`
  - `valorant_register()` - lines 350-640
  - `efootball_register()` - lines 646-935

**Context Variables Added**:
- `is_captain`: Boolean - whether user is team captain
- `already_registered`: Boolean - team already registered
- `pending_request`: RegistrationRequest | None - pending request if exists
- `prefill`: Dict - auto-fill data from user profile

**POST Handler** (for both Valorant and eFootball):
```python
if request.POST.get("action") == "request_approval" and user_team and not is_captain:
    request_message = request.POST.get("request_message", "").strip()
    create_registration_request(
        requester=profile,
        tournament=tournament,
        team=user_team,
        message=request_message
    )
    messages.success(request, "Your request has been sent to your team captain...")
    return redirect(...)
```

### 4. Template UI: Dynamic Display Logic
**Files**:
- `templates/tournaments/valorant_register.html`
- `templates/tournaments/efootball_register.html`

**Display States**:

#### State 1: Already Registered
```django
{% if already_registered %}
    <div class="bg-green-500/10 ...">
        ✓ Already Registered
        Your team is already registered for this tournament.
    </div>
{% endif %}
```

#### State 2: Pending Request
```django
{% elif pending_request %}
    <div class="bg-yellow-500/10 ...">
        ⏳ Request Pending
        You've requested your team captain to register.
        Waiting for captain approval...
    </div>
{% endif %}
```

#### State 3: Non-Captain (can request)
```django
{% elif user_team and not is_captain %}
    <div class="bg-blue-500/10 ...">
        🎮 Request Team Registration
        <form method="post">
            <input type="hidden" name="action" value="request_approval">
            <textarea name="request_message" placeholder="Message to captain..."></textarea>
            <button type="submit">📨 Send Registration Request to Captain</button>
        </form>
    </div>
{% endif %}
```

#### State 4: Captain or No Team (show form)
```django
{% if not already_registered and not pending_request and (is_captain or not user_team) %}
    <form method="post" ...>
        <!-- Full registration form -->
    </form>
{% endif %}
```

## User Flow Examples

### Scenario 1: Non-Captain Wants to Register
1. **User visits tournament page** → redirected to registration page
2. **System checks**:
   - User is authenticated ✓
   - User has a team (Valorant/eFootball) ✓
   - User is NOT captain ✗
3. **Display**: "Request Team Registration" form
4. **User fills** message (optional) and clicks "Send Request"
5. **System**:
   - Creates RegistrationRequest with status=PENDING
   - Sends email to captain with approval link
6. **User sees**: "Your request has been sent to your team captain..."
7. **Next visit**: Shows "⏳ Request Pending" banner

### Scenario 2: Captain Receives Request
1. **Captain gets email**: "Registration request from [Member] for [Tournament]"
2. **Email contains**:
   - Requester details
   - Message from requester
   - Approve button → `/tournaments/approve-request/{request_id}/`
   - Reject button → `/tournaments/reject-request/{request_id}/`
3. **Captain clicks** approve/reject
4. **System**:
   - Updates request status
   - Sends confirmation email to requester
   - If approved: Creates actual Registration automatically (TODO)

### Scenario 3: Captain Registers Directly
1. **Captain visits** tournament registration page
2. **System checks**:
   - User has team ✓
   - User is captain ✓
3. **Display**: Full registration form
4. **Captain fills** and submits
5. **System**:
   - Creates Registration
   - All team members notified
   - Request buttons hidden for all team members

## Profile Auto-Fill Implementation

Both templates now auto-fill from UserProfile:

**Valorant**:
```python
prefill = {
    "full_name": request.user.get_full_name() or request.user.username,
    "email": request.user.email,  # readonly field
    "discord_id": profile.discord_id,
    "riot_id": profile.riot_id,
}
```

**eFootball**:
```python
prefill = {
    "full_name": request.user.get_full_name() or request.user.username,
    "email": request.user.email,  # readonly field
    "discord_id": profile.discord_id,
    "efootball_id": profile.efootball_id,
}
```

**Template Usage**:
```django
<input type="text" name="captain_full_name" value="{{ prefill.full_name }}" />
<input type="email" name="captain_email" value="{{ prefill.email }}" readonly />
<input type="text" name="captain_riot_id" value="{{ prefill.riot_id }}" />
<input type="text" name="captain_discord" value="{{ prefill.discord_id }}" />
```

## Database Prevention

### Duplicate Registration Prevention
**Migration**: `0029_registration_unique_constraints.py` ✅ Applied

**Constraints**:
```python
# One user can only register once per tournament (solo)
UniqueConstraint(
    fields=['tournament', 'user'],
    condition=Q(user__isnull=False),
    name='uq_registration_tournament_user_not_null'
)

# One team can only register once per tournament
UniqueConstraint(
    fields=['tournament', 'team'],
    condition=Q(team__isnull=False),
    name='uq_registration_tournament_team_not_null'
)
```

### Duplicate Request Prevention
**Migration**: `0030_registration_request.py` ✅ Applied

**Constraint**:
```python
# One pending request per requester/team/tournament
UniqueConstraint(
    fields=['requester', 'team', 'tournament'],
    condition=Q(status='pending'),
    name='uq_one_pending_request_per_requester_team_tournament'
)
```

## Email Notifications

### Captain Notification Email
**Trigger**: Non-captain submits request  
**Recipient**: Team captain  
**Subject**: `[DeltaCrown] Registration request for {tournament.title}`  
**Contains**:
- Tournament details
- Requester name and message
- Approve/Reject action buttons
- Direct link to tournament page

### Requester Response Email
**Trigger**: Captain approves/rejects request  
**Recipient**: Original requester  
**Subject**: 
- Approved: `[DeltaCrown] Registration request approved!`
- Rejected: `[DeltaCrown] Registration request declined`
**Contains**:
- Decision notification
- Captain's response message (if provided)
- Next steps or alternative actions

## Testing Checklist

### ✅ Completed
- [x] RegistrationRequest model created and migrated
- [x] Service layer for request creation and emails
- [x] View logic for request handling (Valorant & eFootball)
- [x] Template UI for all states (4 states implemented)
- [x] Profile auto-fill integration
- [x] Duplicate prevention at DB level
- [x] Django system check passes

### 🔄 Pending
- [ ] Captain approval/rejection view handlers
- [ ] Automatic registration creation on approval
- [ ] Captain dashboard to view pending requests
- [ ] Email templates design
- [ ] Request expiry cron job (7 days)
- [ ] Testing with real teams and tournaments

## Code Quality

### Safety Features
1. **Atomic transactions**: All database operations in transactions
2. **Validation error handling**: Proper ValidationError catching
3. **Unique constraints**: DB-level duplicate prevention
4. **Status management**: Enum-based status tracking
5. **Conditional display**: Templates only show relevant UI

### UX Features
1. **Clear messaging**: Different banners for each state
2. **Auto-fill**: Profile data pre-populated
3. **Optional message**: Requester can explain to captain
4. **Immediate feedback**: Success/error messages
5. **No confusion**: Form hidden when not applicable

## Next Steps

### Priority 1: Captain Actions
Create views for approval/rejection:
```python
@login_required
def approve_registration_request(request, request_id):
    # Verify captain
    # Approve request
    # Create actual Registration
    # Send notification email
    pass

@login_required
def reject_registration_request(request, request_id):
    # Verify captain
    # Reject request with message
    # Send notification email
    pass
```

### Priority 2: Captain Dashboard
Add section in team dashboard:
```django
<div class="pending-requests">
    {% for request in pending_requests %}
        <div class="request-card">
            {{ request.requester.display_name }} wants to register for {{ request.tournament.title }}
            <button onclick="approve({{ request.id }})">Approve</button>
            <button onclick="reject({{ request.id }})">Reject</button>
        </div>
    {% endfor %}
</div>
```

### Priority 3: Email Templates
Create HTML email templates:
- `templates/emails/captain_request_notification.html`
- `templates/emails/requester_approval_notification.html`
- `templates/emails/requester_rejection_notification.html`

## Files Modified/Created

### New Files
- `apps/tournaments/models/registration_request.py`
- `apps/tournaments/services/registration_request.py`
- `apps/tournaments/migrations/0030_registration_request.py`
- `docs/NON_CAPTAIN_APPROVAL_WORKFLOW.md`

### Modified Files
- `apps/tournaments/models/__init__.py` - Added RegistrationRequest export
- `apps/tournaments/views/registration_unified.py` - Added request handling
- `templates/tournaments/valorant_register.html` - Added state-based UI
- `templates/tournaments/efootball_register.html` - Added state-based UI
- `apps/ecommerce/models.py` - Fixed defaults for migration

## Summary

The non-captain approval workflow is **70% complete** with core functionality fully implemented:

✅ **Database layer**: Models and migrations  
✅ **Service layer**: Request creation and email notifications  
✅ **View layer**: Request submission handling  
✅ **Template layer**: Dynamic UI based on user role  
✅ **UX layer**: Profile auto-fill and clear messaging  

🔄 **Remaining work**:
- Captain approval/rejection handlers (30% of total)
- Captain dashboard integration
- Email template design
- End-to-end testing

**Impact**: Team members will no longer be frustrated by registration restrictions. Clear workflow guides them to request captain approval instead of hitting dead ends.
