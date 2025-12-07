# Part 4/6: Registration Endpoints & Request/Response Contracts

**Document Purpose**: Catalog the views, URL patterns, HTTP methods, input/output shapes, and data contracts used in tournament registration workflows.

**Audit Date**: December 8, 2025  
**Scope**: Registration endpoints, organizer actions, payment verification, withdrawal flows

---

## 1. Primary Registration Endpoints

### 1.1 Classic Registration Wizard (Production)

**Endpoint**: `/tournaments/<slug>/register/wizard/`  
**View**: `RegistrationWizardView` (`apps/tournaments/views/registration_wizard.py`)  
**Methods**: `GET`, `POST`  
**Authentication**: Required (`LoginRequiredMixin`)

#### GET Request
**Purpose**: Display registration wizard step

**Query Parameters**:
- `type` (optional): `solo` | `team` - Registration mode (auto-detected from tournament)
- `step` (optional): `1` | `2` | `3` - Current wizard step (default: `1`)
- `team_id` (optional): Integer - Team ID for team registrations

**URL Examples**:
```
/tournaments/valorant-championship/register/wizard/?type=solo&step=1
/tournaments/pubg-squad-battle/register/wizard/?type=team&team_id=42&step=2
```

**Response Type**: HTML template  
**Templates Used**:
- Solo: `tournaments/team_registration/solo_step{1,2,3}_enhanced.html`
- Team: `tournaments/team_registration/team_step{1,2,3}_enhanced.html`

**Context Data Passed to Template**:
```python
{
    'tournament': Tournament,              # Tournament model instance
    'current_step': 1,                     # Integer 1-3
    'total_steps': 3,                      # Always 3
    'registration_type': 'solo',           # 'solo' or 'team'
    'autofill_data': {                     # Dict[str, AutoFillField]
        'player_name': AutoFillField(
            value='John Doe',
            source='profile',
            confidence='high',
            missing=False
        ),
        # ... more fields
    },
    'completion_percentage': 85,           # 0-100 integer
    'missing_count': 2,                    # Number of unfilled fields
    'player_data': {                       # Session data (wizard state)
        'player_name': 'John Doe',
        'email': 'john@example.com',
        # ... more fields
    },
    'entry_fee': Decimal('100.00'),        # Step 3 only
    'deltacoin_balance': 250,              # Step 3 only
    'deltacoin_can_afford': True,          # Step 3 only
}
```

#### POST Request - Step 1 (Player/Team Info)
**Purpose**: Save step 1 data to session

**POST Body** (form-encoded):
```
type=solo
step=1
full_name=John Doe
display_name=JohnnyGamer
age=24
country=Bangladesh
riot_id=JohnDoe#1234
platform_server=Asia
rank=Diamond
email=john@example.com
phone=01712345678
discord=johnnygamer#5678
preferred_contact=email
```

**Backend Processing**:
1. Extract all form fields from `request.POST`
2. Save to session: `request.session['registration_wizard_{tournament_id}_solo'] = player_data`
3. Redirect to step 2: `?type=solo&step=2`

**Response**: HTTP 302 redirect to step 2

---

#### POST Request - Step 2 (Review & Terms)
**Purpose**: Accept terms and conditions

**POST Body**:
```
type=solo
step=2
accept_terms=on
```

**Validation**:
- If `accept_terms != 'on'`: Error message + redirect back to step 2
- If valid: Add `terms_accepted: True` + `terms_accepted_at: ISO timestamp` to session

**Response**: HTTP 302 redirect to step 3

---

#### POST Request - Step 3 (Payment Submission)
**Purpose**: Submit payment and create registration record

**POST Body** (DeltaCoin payment):
```
type=solo
step=3
payment_method=deltacoin
```

**POST Body** (Cash payment - bKash/Nagad/Rocket):
```
type=solo
step=3
payment_method=bkash
transaction_id=8D4KL9X2P1
sender_number=01712345678
payment_proof=<file upload>
```

**Backend Processing**:
1. Retrieve wizard data from session
2. Call `RegistrationService.register_participant()` → Creates `Registration` record
3. If DeltaCoin:
   - Call `PaymentService.process_deltacoin_payment()` → Auto-verify
   - Deduct from wallet, set status to `CONFIRMED`
4. If cash method:
   - Call `RegistrationService.submit_payment()` → Create `Payment` record
   - Set status to `PAYMENT_SUBMITTED` (awaiting manual verification)
5. Clear session wizard data
6. Store success data in session
7. Redirect to success page

**Success Response**: HTTP 302 redirect to `/tournaments/<slug>/register/wizard/success/`

**Error Response**: 
- Validation error → Flash message + redirect to step 3
- Example: "Transaction ID is required for bKash payments"

---

### 1.2 Registration Success Page

**Endpoint**: `/tournaments/<slug>/register/wizard/success/`  
**View**: `RegistrationSuccessView` (aliased as `WizardSuccessView`)  
**Method**: `GET`  
**Authentication**: Required

**Session Data Retrieved**:
```python
registration_success = {
    'id': 123,
    'type': 'solo',
    'tournament_slug': 'valorant-championship',
    'player_name': 'JohnnyGamer',
}
```

**Response**: HTML template `tournaments/registration/wizard_success.html`

**Context Data**:
```python
{
    'tournament': Tournament,
    'registration_id': 123,
    'registration_type': 'solo',
    'player_name': 'JohnnyGamer',
}
```

---

## 2. Dynamic Registration (Form Builder)

**Endpoint**: `/tournaments/<slug>/register/`  
**View**: `DynamicRegistrationView` (`apps/tournaments/views/dynamic_registration.py`)  
**Methods**: `GET`, `POST`  
**Feature**: Form builder system with custom fields

**Key Difference from Classic Wizard**:
- Uses `TournamentRegistrationForm` model (dynamic form definition)
- Fields configured via admin/marketplace templates
- Renders via `FormRenderService`
- Stores responses in `FormResponse` model (not `Registration`)

**Not Covered in Detail**: This is a parallel system used for custom tournaments. Classic wizard remains primary production flow.

---

## 3. Registration Status & Payment Tracking

### 3.1 Registration Status View

**Endpoint**: `/tournaments/<slug>/registration/<int:registration_id>/status/`  
**View**: `RegistrationStatusView` (`apps/tournaments/views/payment_status.py`)  
**Method**: `GET`  
**Authentication**: Required  
**Authorization**: Registration owner OR tournament organizer

**Purpose**: Display payment verification status and timeline

**Response**: HTML template `tournaments/registration/status.html`

**Context Data**:
```python
{
    'tournament': Tournament,
    'registration': Registration,
    'current_payment': Payment,           # Most recent payment record
    'payment_history': QuerySet[Payment], # All payment records (ordered by date)
    'status_info': {
        'status': 'PAYMENT_SUBMITTED',
        'icon': '⏳',
        'color': 'yellow',
        'title': 'Payment Pending Verification',
        'message': 'Your payment is being reviewed by organizers.',
        'action': None,                   # or 'resubmit', 'submit_payment'
    },
    'is_organizer': False,
}
```

**Payment Status States** (7 states):
1. `PENDING` - No payment submitted yet (🕐 gray)
2. `SUBMITTED` - Proof uploaded, awaiting verification (⏳ yellow)
3. `VERIFIED` - Approved by organizer (✅ green)
4. `REJECTED` - Rejected, needs resubmission (❌ red)
5. `REFUNDED` - Payment refunded (↩️ blue)
6. `WAIVED` - Fee waived by organizer (⭐ gold)
7. `RESUBMISSION` - Resubmitted after rejection (🔄 orange)

---

### 3.2 Payment Resubmit

**Endpoint**: `/tournaments/<slug>/registration/<int:registration_id>/resubmit/`  
**View**: `PaymentResubmitView`  
**Methods**: `GET`, `POST`  
**Authorization**: Registration owner only

**Purpose**: Allow re-uploading payment proof after rejection

**GET Response**: Form with rejection reason displayed

**POST Body**:
```
payment_method=nagad
transaction_id=9X2KLP4D5
sender_number=01798765432
payment_proof=<new file upload>
```

**Backend Processing**:
1. Create new `Payment` record with status `SUBMITTED`
2. Update `Registration.status` to `PAYMENT_SUBMITTED`
3. Optionally mark old payment as superseded

**Response**: Redirect to status page with success message

---

### 3.3 Download Payment Proof

**Endpoint**: `/tournaments/<slug>/payment/<int:payment_id>/download/`  
**View**: `DownloadPaymentProofView`  
**Method**: `GET`  
**Authorization**: Registration owner OR organizer

**Response Type**: File download  
**HTTP Headers**:
```
Content-Type: image/jpeg (or image/png)
Content-Disposition: attachment; filename="payment_proof_123.jpg"
```

---

## 4. Registration Withdrawal

**Endpoint**: `/tournaments/<slug>/withdraw/`  
**View**: `withdraw_registration_view` (function-based, `apps/tournaments/views/withdrawal.py`)  
**Methods**: `GET`, `POST`  
**Authorization**: Registration owner only

### GET Request
**Purpose**: Show withdrawal confirmation page with refund policy

**Response**: HTML template `tournaments/registration/withdraw.html`

**Context Data**:
```python
{
    'tournament': Tournament,
    'registration': Registration,
    'can_withdraw': True,                 # Boolean
    'withdrawal_blocked_reason': None,    # String if can_withdraw=False
    'refund_info': {
        'refund_eligible': True,
        'refund_percentage': 75,          # Based on days until tournament
        'refund_amount': Decimal('75.00'),
        'policy_text': '75% refund (7+ days before start)',
    },
}
```

**Refund Policy** (example):
- 7+ days before: 75% refund
- 3-6 days before: 50% refund
- < 3 days before: No refund

### POST Request
**Purpose**: Confirm withdrawal

**POST Body**:
```
reason=Schedule conflict, cannot participate
```

**Backend Processing**:
1. Validate withdrawal eligibility (`RegistrationService.can_withdraw()`)
2. Call `RegistrationService.withdraw_registration()`
   - Set `Registration.status = CANCELLED`
   - Set `cancelled_at` timestamp
   - Calculate refund eligibility
   - Create refund record if eligible
   - Unlock team roster if applicable
3. Flash success message with refund details

**Response**: HTTP 302 redirect to tournament detail page

**Error Cases**:
- Tournament already started → "Cannot withdraw after tournament start"
- Already withdrawn → "Registration already cancelled"
- Check-in completed → "Cannot withdraw after checking in"

---

## 5. Organizer Actions (Payment Verification)

### 5.1 Approve Payment

**Endpoint**: `/organizer/<slug>/verify-payment/<int:payment_id>/`  
**View**: `verify_payment` (function-based, `apps/tournaments/views/organizer.py`)  
**Method**: `POST`  
**Authorization**: Tournament organizer OR staff with `approve_payments` permission

**POST Body**: (empty or CSRF token only)

**Backend Processing**:
1. Fetch `Payment` record
2. Check organizer permissions
3. Update `Payment.status = VERIFIED`
4. Update `Payment.verified_at = timezone.now()`
5. Update `Payment.verified_by = request.user`
6. Update `Registration.status = CONFIRMED`
7. Flash success message

**Response**: HTTP 302 redirect to organizer hub payments tab

**Example Message**: "Payment #123 verified successfully. Registration confirmed."

---

### 5.2 Reject Payment

**Endpoint**: `/organizer/<slug>/reject-payment/<int:payment_id>/`  
**View**: `reject_payment` (function-based)  
**Method**: `POST`

**POST Body**:
```
rejection_reason=Transaction ID does not match our records
```

**Backend Processing**:
1. Update `Payment.status = REJECTED`
2. Update `Payment.rejection_reason = <reason>`
3. Update `Payment.rejected_at = timezone.now()`
4. Update `Registration.status = PENDING` (requires resubmission)

**Response**: Redirect + message "Payment rejected. Participant notified to resubmit."

---

### 5.3 Bulk Verify Payments

**Endpoint**: `/organizer/<slug>/bulk-verify-payments/`  
**View**: `bulk_verify_payments`  
**Method**: `POST`

**POST Body**:
```
payment_ids=123,124,125,126
```

**Backend Processing**:
- Loop through payment IDs
- Verify each with same logic as individual verify
- Track success/failure counts

**Response**: Redirect + message "4 payments verified successfully"

---

## 6. Organizer Actions (Registration Management)

### 6.1 Approve Registration

**Endpoint**: `/organizer/<slug>/approve-registration/<int:registration_id>/`  
**View**: `approve_registration`  
**Method**: `POST`  
**Authorization**: Organizer OR staff with `manage_registrations` permission

**Backend Processing**:
1. Update `Registration.status = CONFIRMED`
2. Update `approved_at`, `approved_by`

**Use Case**: Manual approval for no-fee tournaments or waived fees

**Response**: Redirect + "Registration approved"

---

### 6.2 Reject Registration

**Endpoint**: `/organizer/<slug>/reject-registration/<int:registration_id>/`  
**View**: `reject_registration`  
**Method**: `POST`

**POST Body**:
```
rejection_reason=Does not meet age requirement
```

**Backend Processing**:
1. Update `Registration.status = REJECTED`
2. Update `rejection_reason`, `rejected_at`, `rejected_by`

**Response**: Redirect + "Registration rejected"

---

## 7. Auto-Fill Data API (UX Enhancement)

### 7.1 Get Auto-Fill Data (via View Context)

**Not a dedicated API endpoint** - Data fetched server-side and passed to template.

**Backend Call** (in wizard view):
```python
autofill_data = RegistrationAutoFillService.get_autofill_data(
    user=request.user,
    tournament=tournament,
    team=team
)
```

**Data Structure** (returned dict):
```python
{
    'player_name': AutoFillField(
        value='John Doe',
        source='profile',           # 'profile' | 'team' | 'game_account'
        confidence='high',          # 'high' | 'medium' | 'low'
        missing=False,
        field_name='player_name',
    ),
    'email': AutoFillField(
        value='john@example.com',
        source='profile',
        confidence='high',
        missing=False,
        field_name='email',
    ),
    'riot_id': AutoFillField(
        value='JohnDoe#1234',
        source='game_account',
        confidence='high',
        missing=False,
        field_name='riot_id',
    ),
    # Fields not in profile/team → missing=True
    'phone': AutoFillField(
        value=None,
        source=None,
        confidence=None,
        missing=True,
        field_name='phone',
    ),
}
```

**Frontend Usage**:
```django
{% if autofill_data.player_name %}
    <input value="{{ player_data.player_name|default:'' }}">
    {% include 'components/autofill_badge.html' with field=autofill_data.player_name %}
{% endif %}
```

---

### 7.2 Draft Auto-Save (Form Builder Only)

**Endpoint**: `/tournaments/<slug>/register/api/save-draft/`  
**View**: `SaveDraftAPIView` (`apps/tournaments/views/registration_ux_api.py`)  
**Method**: `POST`  
**Content-Type**: `application/json`

**Request Body**:
```json
{
  "player_name": "John Doe",
  "email": "john@example.com",
  "riot_id": "JohnDoe#1234",
  "age": 24
}
```

**Query Parameters**:
- `persist` (optional): `true` | `false` - Save to database (default: false = session only)

**Response**:
```json
{
  "success": true,
  "draft": {
    "saved_at": "2025-12-08T14:30:00Z",
    "field_count": 4
  }
}
```

**Feature**: Used by form builder for auto-save every 30 seconds. **NOT used by classic wizard** (wizard uses session storage only).

---

## 8. Data Flow Summary

### 8.1 Solo Registration Flow (End-to-End)

```
User Action                     Endpoint                                    Backend State Change
─────────────────────────────────────────────────────────────────────────────────────────────────
1. Click "Register"       →     GET /tournaments/X/register/wizard/        None
2. Fill Step 1            →     POST /tournaments/X/register/wizard/       Session['wizard_solo'] saved
3. Review Step 2          →     POST /tournaments/X/register/wizard/       Session['terms_accepted'] = True
4. Submit Payment         →     POST /tournaments/X/register/wizard/       Registration created
                                                                            Payment created (if cash)
                                                                            or DeltaCoin deducted
5. View Success           →     GET /tournaments/X/register/wizard/success/Session['registration_success'] read
6. [Organizer] Verify     →     POST /organizer/X/verify-payment/123/      Payment.status = VERIFIED
                                                                            Registration.status = CONFIRMED
7. [Optional] Withdraw    →     POST /tournaments/X/withdraw/              Registration.status = CANCELLED
                                                                            Refund created (if eligible)
```

---

### 8.2 Team Registration Flow (Key Differences)

```
1. Select Team            →     GET /tournaments/X/register/wizard/?type=team&team_id=42
2. Fill Captain Info      →     POST (step=1, team_id=42)                  Session['wizard_team'] saved
3. Review Roster          →     POST (step=2)                              Team roster validated
4. Team Payment           →     POST (step=3)                              Registration with team_id=42
```

**Team-Specific Fields**:
- `team_id` (IntegerField, not ForeignKey - decoupled from Team model)
- `team_name`, `team_logo`, `captain_name`, etc.

---

## 9. Inconsistencies & Tight Couplings

### 9.1 Multiple Registration Systems

**Problem**: 3 parallel registration systems with overlapping URLs

**Systems**:
1. **Classic Wizard** (production): `/register/wizard/` → Uses `Registration` model
2. **Form Builder** (marketplace): `/register/` → Uses `FormResponse` model
3. **Legacy** (commented): `/register/` (old URL, now redirects)

**URL Collision**:
- `/tournaments/X/register/` → Routes to Form Builder
- `/tournaments/X/register/wizard/` → Routes to Classic Wizard

**Impact**: Confusing for frontend, requires URL parameter to distinguish

---

### 9.2 Session vs Database Storage

**Classic Wizard**: Session-based wizard data
- Pros: No database writes until final submission
- Cons: Lost on session expiration, cannot resume across devices

**Form Builder**: Optional database draft storage
- Pros: Resume from any device
- Cons: Extra database writes

**Inconsistency**: Same feature (registration) uses different storage strategies

---

### 9.3 Payment Status Fragmentation

**Problem**: Payment status stored in TWO places

1. **Payment Model**:
   - `Payment.status` (PENDING, SUBMITTED, VERIFIED, REJECTED, etc.)
2. **Registration Model**:
   - `Registration.status` (PENDING, PAYMENT_SUBMITTED, CONFIRMED, etc.)

**Sync Issues**:
- Must manually keep both in sync
- Example: Verifying payment requires updating BOTH `Payment.status` AND `Registration.status`

**Evidence** (from `verify_payment` function):
```python
# Update payment
payment.status = Payment.VERIFIED
payment.save()

# Also update registration (manual sync)
registration.status = Registration.CONFIRMED
registration.save()
```

---

### 9.4 Hardcoded Game Logic in Auto-Fill

**Problem**: Game-specific field mapping hardcoded in views

**Evidence** (from `registration_wizard.py` line 479):
```python
if game_slug == 'valorant':
    auto_filled['game_id'] = profile.riot_id or ''
elif game_slug == 'pubg-mobile':
    auto_filled['game_id'] = profile.pubg_mobile_id or ''
elif game_slug == 'mobile-legends':
    auto_filled['game_id'] = profile.mlbb_id or ''
# ... 7 total games
```

**Impact on Endpoints**:
- Auto-fill data structure varies by game
- Frontend templates receive different field names (`riot_id` vs `pubg_mobile_id`)
- Adding new game requires code changes to view

**Ideal Solution**:
- `GamePlayerIdentityConfig` should drive field mapping
- View should query: `identity_configs = game_service.get_identity_validation_rules(tournament.game)`

---

### 9.5 Team ID as IntegerField (Loose Coupling)

**Problem**: `Registration.team_id` is IntegerField, not ForeignKey

**Implications for Endpoints**:
- POST body accepts raw integer: `team_id=42`
- No database-level constraint validation
- Organizer views must manually join to Team model to display team names
- Risk of orphaned team_id values if team deleted

**Example POST Body**:
```
team_id=999999  # Could be non-existent team, no validation error
```

---

### 9.6 Form Submission Methods

**Classic Wizard**: Traditional HTML form POST + redirect
```html
<form method="POST" action="/tournaments/X/register/wizard/">
    {% csrf_token %}
    <input name="step" value="3">
    <button type="submit">Submit</button>
</form>
```

**Form Builder**: AJAX submission (optional)
```javascript
fetch('/tournaments/X/register/api/save-draft/', {
    method: 'POST',
    body: JSON.stringify(formData),
    headers: {'Content-Type': 'application/json'}
})
```

**Inconsistency**: Same user-facing feature uses different submission patterns

---

## 10. Request/Response Shape Examples

### 10.1 Registration Creation (Successful)

**Request**:
```http
POST /tournaments/valorant-championship/register/wizard/ HTTP/1.1
Content-Type: application/x-www-form-urlencoded
Cookie: sessionid=abc123...

type=solo&step=3&payment_method=deltacoin
```

**Response** (successful DeltaCoin payment):
```http
HTTP/1.1 302 Found
Location: /tournaments/valorant-championship/register/wizard/success/
Set-Cookie: messages=...
```

**Database Changes**:
```sql
INSERT INTO tournaments_registration (
    tournament_id, user_id, team_id, status, game_id, phone, discord, ...
) VALUES (
    1, 42, NULL, 'CONFIRMED', 'JohnDoe#1234', '01712345678', ...
);

UPDATE economy_deltacrownwallet
SET balance = balance - 100
WHERE user_id = 42;

INSERT INTO economy_transaction (
    wallet_id, transaction_type, amount, ...
) VALUES (...);
```

---

### 10.2 Payment Rejection (Organizer Action)

**Request**:
```http
POST /organizer/valorant-championship/reject-payment/123/ HTTP/1.1
Content-Type: application/x-www-form-urlencoded

rejection_reason=Transaction+ID+mismatch
```

**Response**:
```http
HTTP/1.1 302 Found
Location: /organizer/valorant-championship/hub/payments/
Set-Cookie: messages="Payment rejected. Participant notified."
```

**Database Changes**:
```sql
UPDATE tournaments_payment
SET status = 'REJECTED',
    rejection_reason = 'Transaction ID mismatch',
    rejected_at = '2025-12-08 14:45:00',
    rejected_by_id = 1
WHERE id = 123;

UPDATE tournaments_registration
SET status = 'PENDING'
WHERE id = (SELECT registration_id FROM tournaments_payment WHERE id = 123);
```

**Email Notification** (triggered):
- To: Participant email
- Subject: "Payment Rejected - Resubmission Required"
- Body: Includes rejection reason + resubmit link

---

### 10.3 Withdrawal with Refund

**Request**:
```http
POST /tournaments/valorant-championship/withdraw/ HTTP/1.1
Content-Type: application/x-www-form-urlencoded

reason=Personal+emergency
```

**Response**:
```http
HTTP/1.1 302 Found
Location: /tournaments/valorant-championship/
Set-Cookie: messages="Registration withdrawn. 75% refund (৳75.00) will be processed."
```

**Database Changes**:
```sql
UPDATE tournaments_registration
SET status = 'CANCELLED',
    cancelled_at = '2025-12-08 15:00:00',
    cancellation_reason = 'Personal emergency'
WHERE id = 123;

INSERT INTO economy_refund (
    registration_id, amount, refund_percentage, status, ...
) VALUES (
    123, 75.00, 75, 'PENDING', ...
);
```

---

## 11. Missing Endpoints (Gaps)

### 11.1 No API for Real-Time Validation

**Current State**: HTML5 validation only (client-side)

**Desired**: `/tournaments/X/register/api/validate-field/`
- POST `{"field": "riot_id", "value": "JohnDoe#1234"}`
- Response: `{"valid": true}` or `{"valid": false, "error": "Invalid Riot ID format"}`

**Use Case**: Real-time feedback as user types

---

### 11.2 No Eligibility Check API

**Current State**: Eligibility checked on GET request to wizard

**Desired**: `/tournaments/X/register/api/check-eligibility/`
- GET request
- Response: `{"eligible": true, "reasons": []}` or `{"eligible": false, "reasons": ["Already registered", "Under 18"]}`

**Use Case**: Check eligibility before showing "Register" button on detail page

---

### 11.3 No Payment Status Webhook

**Current State**: Organizers manually verify payments in admin panel

**Desired**: Webhook endpoint for payment gateway callbacks
- `/tournaments/payments/webhook/bkash/`
- Auto-verify payments from bKash API confirmation

---

## 12. URL Patterns Reference Table

| URL Pattern | View | Method | Purpose |
|-------------|------|--------|---------|
| `<slug>/register/wizard/` | `RegistrationWizardView` | GET, POST | Classic registration wizard (production) |
| `<slug>/register/wizard/success/` | `WizardSuccessView` | GET | Success page after submission |
| `<slug>/register/` | `DynamicRegistrationView` | GET, POST | Form builder registration |
| `<slug>/registration/<id>/status/` | `RegistrationStatusView` | GET | View payment/registration status |
| `<slug>/registration/<id>/resubmit/` | `PaymentResubmitView` | GET, POST | Resubmit payment after rejection |
| `<slug>/payment/<id>/download/` | `DownloadPaymentProofView` | GET | Download payment screenshot |
| `<slug>/withdraw/` | `withdraw_registration_view` | GET, POST | Cancel registration with refund |
| `organizer/<slug>/verify-payment/<id>/` | `verify_payment` | POST | Approve payment (organizer) |
| `organizer/<slug>/reject-payment/<id>/` | `reject_payment` | POST | Reject payment (organizer) |
| `organizer/<slug>/approve-registration/<id>/` | `approve_registration` | POST | Approve registration (organizer) |
| `organizer/<slug>/reject-registration/<id>/` | `reject_registration` | POST | Reject registration (organizer) |
| `organizer/<slug>/bulk-verify-payments/` | `bulk_verify_payments` | POST | Bulk verify payments (organizer) |
| `<slug>/register/api/save-draft/` | `SaveDraftAPIView` | POST | Auto-save draft (form builder only) |
| `<slug>/register/api/get-draft/` | `GetDraftAPIView` | GET | Retrieve draft (form builder only) |

---

## 13. Key Takeaways

### 13.1 Strengths
1. ✅ **Clear separation**: Participant vs organizer endpoints
2. ✅ **Session-based wizard**: No database pollution from incomplete registrations
3. ✅ **Authorization checks**: Owner-only access to status/withdrawal pages
4. ✅ **Redirect-based flow**: Traditional POST-redirect-GET pattern (prevents double submission)

### 13.2 Weaknesses
1. ❌ **Multiple registration systems**: 3 overlapping systems (wizard, form builder, legacy)
2. ❌ **Dual status tracking**: Payment + Registration statuses must stay synced manually
3. ❌ **No real-time validation**: Only HTML5 client-side validation
4. ❌ **Hardcoded game logic**: Auto-fill mapping requires code changes per game
5. ❌ **Loose team coupling**: IntegerField team_id (no ForeignKey constraint)
6. ❌ **No API-first design**: All endpoints return HTML (no JSON API for frontend frameworks)

### 13.3 Technical Debt
1. **Consolidate registration systems**: Pick one (wizard OR form builder), deprecate others
2. **Single source of truth**: Merge Payment.status and Registration.status into unified state machine
3. **API layer**: Create `/api/tournaments/X/registration/` RESTful endpoint
4. **Dynamic game fields**: Replace hardcoded if-else with GamePlayerIdentityConfig lookups
5. **ForeignKey team_id**: Add proper relationship constraint (or use XOR with IntegerField)

---

**End of Part 4: Registration Endpoints & Request/Response Contracts**

**Next**: Part 5 - Match/Bracket/Result Processing (Out of scope for registration audit)  
**Alternative Next**: Part 6 - Recommendations & Modernization Roadmap
