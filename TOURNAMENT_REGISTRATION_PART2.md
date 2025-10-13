# Tournament Registration System - Part 2: Workflows & Integration

## 6. Business Logic & Workflows

### 6.1 Registration Workflows

#### 6.1.1 Solo Tournament Registration Flow

```
User clicks "Register" button
    ↓
System checks:
  - Is user authenticated? → Login required
  - Is registration open? → Check dates
  - Are slots available? → Check capacity
  - Is user already registered? → Check duplicates
    ↓
[ELIGIBLE] Show registration form
    ↓
User fills form:
  - Personal info (auto-filled from profile)
  - In-game credentials
  - Payment info (if entry_fee > 0)
  - Agree to rules
    ↓
User clicks "Submit"
    ↓
System validates:
  - Required fields present
  - Phone format correct
  - Email format valid
  - Payment reference provided (if paid)
    ↓
[VALID] Create Registration:
  - status = 'PENDING'
  - payment_status = 'pending'
  - Save to database
    ↓
Update capacity counter:
  - TournamentCapacity.current_teams += 1
    ↓
Send confirmation email
    ↓
Redirect to success page
```

---

#### 6.1.2 Team Tournament Registration Flow (Captain)

```
Captain clicks "Register Team" button
    ↓
System checks:
  - Is captain authenticated?
  - Is captain of an active team?
  - Is registration open?
  - Are slots available?
  - Is team already registered?
    ↓
[ELIGIBLE] Show registration form
    ↓
Form auto-fills:
  - Team name, tag, logo
  - Captain's contact info
  - Team member count
    ↓
Captain fills remaining:
  - Payment info (if entry_fee > 0)
  - Team roster screenshot (if required)
  - Agree to rules on behalf of team
    ↓
Captain clicks "Submit"
    ↓
System validates:
  - Team meets min/max player requirements
  - All required fields present
  - Payment info valid
    ↓
[VALID] Create Registration:
  - tournament = Tournament
  - team = Team
  - user = NULL (team registration)
  - status = 'PENDING'
  - payment_status = 'pending'
    ↓
Update capacity counter
    ↓
Notify team members (optional)
    ↓
Redirect to success page
```

---

#### 6.1.3 Team Tournament Registration Flow (Non-Captain)

```
Team Member clicks "Register Team" button
    ↓
System detects:
  - User is team member but NOT captain
    ↓
Show "Request Approval" interface:
  - Display: "Only your team captain can register"
  - Option: "Request Captain Approval"
    ↓
Member clicks "Request Approval"
    ↓
System creates RegistrationRequest:
  - tournament = Tournament
  - team = Team
  - requested_by = Member
  - status = 'PENDING'
    ↓
Notify captain:
  - Email: "Team member requests tournament registration"
  - Dashboard notification
  - In-app badge on captain's dashboard
    ↓
Captain reviews request:
  - View tournament details
  - View entry fee
  - View team roster
    ↓
Captain decides:

  [APPROVE PATH]
    ↓
  Captain fills payment info
    ↓
  System creates Registration
    ↓
  RegistrationRequest.status = 'APPROVED'
    ↓
  Notify team member: "Your request was approved!"
    ↓
  Email confirmation to all team members

  [REJECT PATH]
    ↓
  Captain provides rejection reason
    ↓
  RegistrationRequest.status = 'REJECTED'
    ↓
  Notify team member: "Your request was rejected"
    ↓
  Show rejection reason
```

---

### 6.2 Validation Rules

#### 6.2.1 Field Validations

| Field | Rules | Format | Example |
|-------|-------|--------|---------|
| **display_name** | Required for solo | 3-50 chars | `ProGamer123` |
| **email** | Required | Valid email | `player@example.com` |
| **phone** | Required | BD mobile | `01712345678`, `+8801712345678` |
| **in_game_id** | Conditional | Game-specific | Valorant: `Player#1234`, eFootball: `12345678` |
| **in_game_username** | Conditional | 3-30 chars | `ProGamer` |
| **discord_id** | Optional | Discord format | `username#1234` or `@username` |
| **payment_method** | Required if fee > 0 | Enum | `bkash`, `nagad`, `rocket`, `bank` |
| **payer_account_number** | Required if fee > 0 | BD mobile | `01712345678` |
| **payment_reference** | Required if fee > 0 | 6-50 chars | `ABC123DEF456` |
| **agree_rules** | Required | Boolean | `true` |

#### 6.2.2 Business Rules

**Registration Eligibility:**
1. User must be authenticated
2. Registration must be open (within reg_open_at and reg_close_at)
3. Tournament must have available slots
4. User/Team must not be already registered
5. For team events: User must be in an active team
6. For non-captain: Approval request must be pending or approved

**Payment Rules:**
1. If `entry_fee` > 0:
   - `payment_method` is required
   - `payer_account_number` is required
   - `payment_reference` is required
2. If `entry_fee` == 0 or NULL:
   - Payment fields are optional

**Team Rules:**
1. Team size must be between `min_players_per_team` and `max_players_per_team`
2. Team must have an active captain
3. Only captain can directly register team
4. Non-captain members can request approval

**Capacity Rules:**
1. If `slot_size` or `TournamentCapacity.max_teams` is set:
   - Check `current_teams < max_teams`
   - Block registration if full
2. If waitlist enabled:
   - Add to waitlist when main capacity full
   - Promote from waitlist when slot opens

---

### 6.3 State Machine

#### 6.3.1 Registration Status States

```
[NEW] → [PENDING] → [CONFIRMED] → [ACTIVE]
                ↓        ↓
           [CANCELLED] [REJECTED]
```

**State Definitions:**

| State | Meaning | Next States | Trigger |
|-------|---------|-------------|---------|
| **PENDING** | Awaiting payment verification | CONFIRMED, CANCELLED | Admin verifies payment OR User cancels |
| **CONFIRMED** | Payment verified, registration active | CANCELLED | Admin or automated check-in |
| **CANCELLED** | Registration cancelled | (Terminal) | User withdrawal OR Admin action |

---

#### 6.3.2 Payment Status States

```
[pending] → [verified] → Registration active
        ↓
     [rejected] → Notify user
```

**State Definitions:**

| State | Meaning | Action Required |
|-------|---------|-----------------|
| **pending** | Payment submitted, awaiting verification | Admin must verify |
| **verified** | Payment confirmed by admin | Auto-update to CONFIRMED |
| **rejected** | Payment invalid or fraudulent | Notify user, keep PENDING |

---

#### 6.3.3 Approval Request States

```
[PENDING] → [APPROVED] → Create Registration
        ↓
    [REJECTED] → Notify member
        ↓
    [EXPIRED] → Auto-close after deadline
```

---

### 6.4 Payment Verification Workflow

```
User submits registration with payment info
    ↓
Registration created with payment_status = 'pending'
    ↓
Admin receives notification:
  - Dashboard shows pending payments
  - Filter: "Pending Verifications"
    ↓
Admin reviews payment:
  - Check payment_method (bkash/nagad/etc.)
  - Verify payer_account_number
  - Confirm payment_reference in payment gateway
  - Check amount matches entry_fee
    ↓
Admin decides:

  [VERIFY PATH]
    ↓
  Admin clicks "Verify Payment"
    ↓
  System updates:
    - payment_status = 'verified'
    - payment_verified_by = admin_user
    - payment_verified_at = now()
    - status = 'CONFIRMED'
    ↓
  Send email: "Payment verified! Registration confirmed."
    ↓
  Update slot counter

  [REJECT PATH]
    ↓
  Admin clicks "Reject Payment"
    ↓
  Admin provides rejection reason
    ↓
  System updates:
    - payment_status = 'rejected'
    - Keep status = 'PENDING'
    ↓
  Send email: "Payment verification failed. Please contact support."
    ↓
  User can resubmit with correct payment info
```

---

### 6.5 Capacity Management

#### 6.5.1 Slot Tracking

**Real-time Updates:**
```python
# When registration created:
tournament.capacity.current_teams += 1
tournament.capacity.save()

# When registration cancelled:
tournament.capacity.current_teams -= 1
tournament.capacity.save()

# Check if full:
is_full = tournament.capacity.current_teams >= tournament.capacity.max_teams
```

#### 6.5.2 Waitlist System

**When Main Capacity Full:**
```python
if tournament.capacity.is_full and tournament.capacity.enable_waitlist:
    if tournament.capacity.current_waitlist < tournament.capacity.waitlist_capacity:
        # Add to waitlist
        registration.on_waitlist = True
        registration.save()
        tournament.capacity.current_waitlist += 1
    else:
        # Waitlist also full
        raise ValidationError("Tournament and waitlist are both full")
```

**Promoting from Waitlist:**
```python
# When confirmed registration is cancelled:
if cancelled_registration.status == 'CONFIRMED':
    # Get first waitlist registration
    waitlist_reg = Registration.objects.filter(
        tournament=tournament,
        on_waitlist=True,
        status='CONFIRMED'
    ).order_by('created_at').first()
    
    if waitlist_reg:
        waitlist_reg.on_waitlist = False
        waitlist_reg.save()
        tournament.capacity.current_waitlist -= 1
        # Notify: "You've been moved from waitlist to main roster!"
```

---

## 7. Frontend Integration Guide

### 7.1 Registration Form Requirements

#### 7.1.1 HTML Structure

```html
<form id="registration-form" method="POST" enctype="multipart/form-data">
    {% csrf_token %}
    
    <!-- Step 1: Personal Info -->
    <div class="form-step" data-step="1">
        <input type="text" name="display_name" id="id_display_name" required>
        <input type="email" name="email" id="id_email" required>
        <input type="tel" name="phone" id="id_phone" required>
    </div>
    
    <!-- Step 2: Game Credentials -->
    <div class="form-step" data-step="2">
        <input type="text" name="in_game_id" id="id_in_game_id">
        <input type="text" name="in_game_username" id="id_in_game_username">
        <input type="text" name="discord_id" id="id_discord_id">
    </div>
    
    <!-- Step 3: Payment (if entry_fee > 0) -->
    <div class="form-step" data-step="3" id="payment-step">
        <select name="payment_method" id="id_payment_method" required>
            <option value="bkash">bKash</option>
            <option value="nagad">Nagad</option>
            <option value="rocket">Rocket</option>
            <option value="bank">Bank Transfer</option>
        </select>
        <input type="text" name="payer_account_number" required>
        <input type="text" name="payment_reference" required>
    </div>
    
    <!-- Step 4: Confirmation -->
    <div class="form-step" data-step="4">
        <label>
            <input type="checkbox" name="agree_rules" required>
            I agree to the tournament rules
        </label>
    </div>
    
    <button type="button" id="btn-prev">Previous</button>
    <button type="button" id="btn-next">Next</button>
    <button type="submit" id="btn-submit">Register</button>
</form>
```

---

#### 7.1.2 JavaScript Implementation

**Auto-fill Example:**
```javascript
// Auto-fill user profile data
async function autoFillProfileData() {
    const slug = document.querySelector('[data-tournament-slug]').dataset.tournamentSlug;
    
    const response = await fetch(`/api/${slug}/register/context/`);
    const data = await response.json();
    
    if (data.success && data.context) {
        // Fill form fields
        document.getElementById('id_display_name').value = data.profile_data.display_name || '';
        document.getElementById('id_email').value = data.profile_data.email || '';
        document.getElementById('id_phone').value = data.profile_data.phone || '';
    }
}
```

**Real-time Validation:**
```javascript
// Validate phone field
document.getElementById('id_phone').addEventListener('blur', function() {
    const phone = this.value;
    const bdMobileRegex = /^(?:\+?880|0)1[0-9]{9}$/;
    
    if (!bdMobileRegex.test(phone.replace(/\s/g, ''))) {
        showFieldError(this, 'Enter a valid Bangladeshi mobile number');
    } else {
        clearFieldError(this);
    }
});
```

**Form Submission:**
```javascript
document.getElementById('registration-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const slug = this.dataset.tournamentSlug;
    
    // Show loading state
    const submitBtn = document.getElementById('btn-submit');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
    
    try {
        const response = await fetch(`/api/${slug}/register/submit/`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            window.location.href = result.redirect_url;
        } else {
            displayErrors(result.errors);
        }
    } catch (error) {
        alert('An error occurred. Please try again.');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Register';
    }
});
```

---

### 7.2 UI State Management

#### 7.2.1 Registration Button States

```javascript
async function updateRegistrationButtonState() {
    const btn = document.getElementById('register-button');
    const slug = btn.dataset.tournamentSlug;
    
    const response = await fetch(`/api/${slug}/register/context/`);
    const data = await response.json();
    
    if (data.context.can_register) {
        btn.disabled = false;
        btn.className = 'btn btn-primary';
        btn.textContent = data.context.button_text;
    } else {
        btn.disabled = true;
        btn.className = 'btn btn-secondary';
        btn.textContent = data.context.button_text;
        btn.title = data.context.reason;
    }
}
```

---

#### 7.2.2 Real-time Slot Counter

```javascript
async function updateSlotCounter() {
    const slug = document.querySelector('[data-tournament-slug]').dataset.tournamentSlug;
    const response = await fetch(`/api/${slug}/state/`);
    const data = await response.json();
    
    if (data.success) {
        const { total, taken, available } = data.state.capacity;
        
        document.getElementById('slot-counter').textContent = `${taken}/${total} slots filled`;
        
        const percentage = (taken / total) * 100;
        document.getElementById('capacity-bar').style.width = `${percentage}%`;
        
        if (available <= 5) {
            showWarning(`Only ${available} slots remaining!`);
        }
    }
}

// Update every 30 seconds
setInterval(updateSlotCounter, 30000);
```

---

## 8. Payment Integration

### 8.1 Supported Payment Methods

| Method | Code | Format | Example |
|--------|------|--------|---------|
| **bKash** | `bkash` | BD mobile | `01712345678` |
| **Nagad** | `nagad` | BD mobile | `01812345678` |
| **Rocket** | `rocket` | BD mobile | `01912345678` |
| **Bank Transfer** | `bank` | Account number | `1234567890123` |

---

### 8.2 Payment Flow

```
User selects payment method
    ↓
System displays payment instructions
    ↓
User completes payment externally
    ↓
User returns and enters:
  - Sender account/mobile number
  - Transaction ID
    ↓
User submits registration
    ↓
System saves payment info (status = 'pending')
    ↓
Admin verifies payment
    ↓
[VERIFIED] → Registration confirmed
[REJECTED] → User notified
```

---

### 8.3 Admin Payment Verification

```
Admin views pending payments
    ↓
Verifies in payment gateway
    ↓
Admin clicks "Verify" or "Reject"
    ↓
System updates registration status
    ↓
User receives email notification
```

---

## 9. Game-Specific Configurations

### 9.1 eFootball Mobile

**Required Fields:**
- `in_game_username`: eFootball username
- `in_game_id`: eFootball  user ID (numeric)
- `team_screenshot`: Optional roster screenshot

**Example Configuration:**
```python
tournament.efootball_config.ask_username = True
tournament.efootball_config.require_ingame_id = True
tournament.efootball_config.ask_roster_screenshot = True
```

---

### 9.2 Valorant

**Required Fields:**
- `in_game_id`: Riot ID (format: `Username#TAG`)
- `discord_id`: Discord for team communication

**Example Configuration:**
```python
tournament.valorant_config.require_riot_id = True
tournament.valorant_config.require_discord = True
```

---

## 10. Security & Validation

### 10.1 CSRF Protection

All POST requests must include CSRF token:
```html
<form method="POST">
    {% csrf_token %}
    <!-- form fields -->
</form>
```

### 10.2 Authentication

All registration endpoints require authentication:
```python
@login_required
def modern_register_view(request, slug):
    # ...
```

### 10.3 Permission Checks

- Captain approval: Verify user is team captain
- Payment verification: Verify user has admin/staff role
- Registration edit: Verify user owns the registration

### 10.4 Rate Limiting

Implement rate limiting on registration endpoints:
- Maximum 5 registration attempts per hour per user
- Maximum 3 validation requests per minute per user

---

## 11. Testing Guide

### 11.1 Unit Tests

Test registration service methods:
```python
def test_create_registration_solo():
    user = UserFactory()
    tournament = TournamentFactory(tournament_type='SOLO')
    
    registration = RegistrationService.create_registration(
        tournament=tournament,
        user=user,
        data={
            'display_name': 'TestPlayer',
            'email': 'test@example.com',
            'phone': '01712345678'
        }
    )
    
    assert registration.status == 'PENDING'
    assert registration.user == user.profile
```

### 11.2 Integration Tests

Test full registration flow:
```python
def test_team_registration_flow():
    # Create tournament and team
    tournament = TournamentFactory(tournament_type='TEAM')
    team = TeamFactory()
    captain = team.captain
    
    # Captain registers team
    client.force_login(captain.user)
    response = client.post(f'/tournaments/register-modern/{tournament.slug}/', {
        'payment_method': 'bkash',
        'payer_account_number': '01712345678',
        'payment_reference': 'ABC123',
        'agree_rules': True
    })
    
    assert response.status_code == 302
    assert Registration.objects.filter(tournament=tournament, team=team).exists()
```

---

## 12. Deployment Checklist

### 12.1 Pre-Deployment

- [ ] Run migrations: `python manage.py migrate`
- [ ] Collect static files: `python manage.py collectstatic`
- [ ] Test all API endpoints
- [ ] Verify payment gateway integration
- [ ] Test email notifications
- [ ] Check database indexes

### 12.2 Configuration

```python
# settings.py

# Tournament settings
TOURNAMENT_REGISTRATION_TIMEOUT = 3600  # 1 hour
TOURNAMENT_AUTO_CLOSE_ON_FULL = True
TOURNAMENT_ENABLE_WAITLIST = True

# Payment settings
PAYMENT_VERIFICATION_EMAIL = 'payments@deltacrown.com'
PAYMENT_GATEWAY_TIMEOUT = 30  # seconds

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
```

---

## 13. Migration Path

### 13.1 From Old Registration System

```python
# Migration script
from apps.tournaments.models import Registration, Tournament

# Update existing registrations
old_regs = OldRegistration.objects.all()
for old_reg in old_regs:
    Registration.objects.create(
        tournament=old_reg.tournament,
        user=old_reg.user_profile,
        team=old_reg.team,
        payment_method=old_reg.payment_type,
        payment_reference=old_reg.trx_id,
        payment_status='verified',
        status='CONFIRMED',
        created_at=old_reg.created_at
    )
```

---

## 14. Troubleshooting

### 14.1 Common Issues

**Issue: "Tournament is full" but slots available**
- Check `TournamentCapacity.current_teams` vs confirmed registrations
- Run: `python manage.py fix_tournament_capacity`

**Issue: Payment verification not working**
- Verify admin has proper permissions
- Check `payment_status` field values
- Ensure email notifications are configured

**Issue: Team captain cannot register**
- Check `TeamMembership.role == 'CAPTAIN'`
- Verify `Team.captain` field is set
- Check team status is 'ACTIVE'

---

## 15. Support & Contact

**Documentation:** `/docs/tournament-registration/`  
**API Reference:** `/api/docs/`  
**Support Email:** `support@deltacrown.com`  
**Developer Team:** DeltaCrown Development

---

**END OF DOCUMENTATION**

