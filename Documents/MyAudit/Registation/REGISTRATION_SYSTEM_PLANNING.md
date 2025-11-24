# Tournament Registration System - Complete Planning Specification

**Document Type:** Planning Specification Report  
**Created:** November 24, 2025  
**Source Documents:**
- `Documents/Planning/PROPOSAL_PART_1_EXECUTIVE_SUMMARY.md`
- `Documents/Planning/PART_2.1_ARCHITECTURE_FOUNDATIONS.md`
- `Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md`
- `Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md`
- `Documents/Planning/PART_4.4_REGISTRATION_PAYMENT_FLOW.md`
- `Documents/Planning/PART_5.1_IMPLEMENTATION_ROADMAP_SPRINT_PLANNING.md`

---

## Executive Summary

The DeltaCrown Tournament Registration System is designed as a comprehensive, user-friendly platform for tournament participant registration with flexible payment verification. This document synthesizes all planning documentation to provide a complete specification of the planned registration system.

**Key Objectives:**
1. Enable seamless tournament registration for both solo players and teams
2. Support multiple payment methods (DeltaCoin, bKash, Nagad, Rocket, Bank Transfer)
3. Provide admin payment verification workflow with audit trails
4. Auto-fill registration data from user profiles
5. Handle waitlists, capacity limits, and fee waivers
6. Ensure mobile-first responsive design

---

## 1. System Architecture

### 1.1 Service Layer Design

**Location:** `apps/tournaments/services/registration_service.py`

**Core Services:**

```python
class RegistrationService:
    """Business logic for tournament registration"""
    
    @staticmethod
    def register_participant(tournament_id, user, team_id=None, registration_data=None) -> Registration
        """Register user/team for tournament with eligibility checks"""
    
    @staticmethod
    def submit_payment(registration_id, payment_method, amount, transaction_id='', payment_proof='') -> Payment
        """Create payment record for registration"""
    
    @staticmethod
    def submit_payment_proof(registration_id, payment_proof_file, reference_number='', notes='') -> Payment
        """Upload payment proof screenshot/PDF"""
    
    @staticmethod
    def verify_payment(payment_id, verified_by, admin_notes='') -> Payment
        """Admin verification of payment (approve)"""
    
    @staticmethod
    def reject_payment(payment_id, rejected_by, reason) -> Payment
        """Admin rejection of payment with reason"""
    
    @staticmethod
    def refund_payment(payment_id, refunded_by, reason='') -> Payment
        """Process payment refund"""
    
    @staticmethod
    def cancel_registration(registration_id, user, reason='') -> Registration
        """Cancel registration with soft delete"""
```

**Integration Points:**
- `apps.user_profile`: Auto-fill game IDs and contact information
- `apps.teams`: Fetch team roster and validate captain permissions
- `apps.economy`: DeltaCoin payment deduction (future)
- `apps.notifications`: Registration confirmations and payment status updates (future)

### 1.2 Database Design

**Registration Model:** `apps/tournaments/models/registration.py`

```python
class Registration(SoftDeleteModel, TimestampedModel):
    """Participant registration tracking"""
    
    # Core fields
    tournament = ForeignKey(Tournament)
    user = ForeignKey(User, null=True)  # Solo or team captain
    team_id = IntegerField(null=True)  # IntegerField reference to apps.teams
    
    # JSONB data storage
    registration_data = JSONField(default=dict)  # Flexible participant data
    
    # Status workflow
    status = CharField(choices=[
        'pending',            # Registered, awaiting payment
        'payment_submitted',  # Payment proof uploaded
        'confirmed',          # Payment verified
        'rejected',           # Payment/registration rejected
        'cancelled',          # User cancelled
        'no_show'            # Failed check-in
    ])
    
    # Bracket assignment
    slot_number = IntegerField(null=True, unique_per_tournament=True)
    seed = IntegerField(null=True)  # For ranked seeding
    
    # Check-in tracking
    checked_in = BooleanField(default=False)
    checked_in_at = DateTimeField(null=True)
    
    # Soft delete support
    is_deleted = BooleanField(default=False)
    deleted_at = DateTimeField(null=True)
    deleted_by = ForeignKey(User, null=True)
```

**Payment Model:**

```python
class Payment(models.Model):
    """Payment proof and verification"""
    
    registration = OneToOneField(Registration)
    
    payment_method = CharField(choices=[
        'bkash', 'nagad', 'rocket', 'bank', 'deltacoin'
    ])
    
    amount = DecimalField(max_digits=10, decimal_places=2)
    transaction_id = CharField(max_length=200, blank=True)
    reference_number = CharField(max_length=100, blank=True)
    
    # File upload
    payment_proof = FileField(upload_to='payment_proofs/%Y/%m/')
    file_type = CharField(choices=['IMAGE', 'PDF'])
    
    # Verification workflow
    status = CharField(choices=[
        'pending',    # Payment created
        'submitted',  # Proof uploaded
        'verified',   # Admin approved
        'rejected',   # Admin rejected
        'refunded'    # Refunded to user
    ])
    
    admin_notes = TextField(blank=True)
    verified_by = ForeignKey(User, null=True)
    verified_at = DateTimeField(null=True)
```

**Constraints & Indexes:**

```sql
-- Registration constraints
ALTER TABLE registration ADD CONSTRAINT chk_participant_type 
    CHECK ((user_id IS NOT NULL AND team_id IS NULL) OR (user_id IS NULL AND team_id IS NOT NULL));

CREATE UNIQUE INDEX idx_registration_user_tournament 
    ON registration(tournament_id, user_id) WHERE user_id IS NOT NULL AND is_deleted = false;

CREATE UNIQUE INDEX idx_registration_team_tournament 
    ON registration(tournament_id, team_id) WHERE team_id IS NOT NULL AND is_deleted = false;

CREATE INDEX idx_registration_status ON registration(status);
CREATE INDEX idx_registration_data_gin ON registration USING GIN(registration_data);

-- Payment constraints
ALTER TABLE payment ADD CONSTRAINT chk_payment_amount_positive CHECK (amount > 0);
ALTER TABLE payment ADD CONSTRAINT chk_payment_verification 
    CHECK ((status = 'verified' AND verified_by_id IS NOT NULL AND verified_at IS NOT NULL) OR (status != 'verified'));

CREATE INDEX idx_payment_status ON payment(status);
CREATE INDEX idx_payment_method ON payment(payment_method);
```

---

## 2. User Interface Design

### 2.1 Registration Wizard Flow

**URL:** `/tournaments/<slug>/register`

**Multi-Step Wizard:**

1. **Step 1: Eligibility Check**
   - Display: Tournament name, dates, requirements
   - Check: User logged in, not already registered, capacity available
   - Action: Continue if eligible, else show reason

2. **Step 2: Team Selection** (if team tournament)
   - Display: User's existing teams for this game
   - Select: Team from dropdown
   - Validate: Team size matches tournament requirements
   - Option: Create new team inline

3. **Step 3: Player Information** (if solo) / Team Roster Verification (if team)
   - **Solo:**
     - Auto-fill: Name, email, Discord ID from user profile
     - Manual entry: In-game ID, phone number
   - **Team:**
     - Display: Team members (read-only)
     - Confirm: All members available and aware

4. **Step 4: Custom Fields**
   - Render: Tournament-specific custom fields dynamically
   - Types: Text, Number, Media, Toggle, Date, URL, Dropdown
   - Validate: Required fields, format constraints
   - Examples:
     - "Riot ID" (text, required)
     - "Discord Username" (text)
     - "Team Logo URL" (URL, optional)
     - "Preferred Communication" (dropdown: Discord/WhatsApp/Telegram)

5. **Step 5: Review & Confirm**
   - Summary: All registration data
   - Rules: Expandable tournament rules section
   - Consent: Checkbox "I have read and accept the rules"
   - Notice: Entry fee requirement if applicable
   - Action: Register button (disabled until consent checked)

**Session Management:**
- Store wizard state in `request.session` with key `registration_wizard_{tournament_id}`
- Allow back navigation between steps
- Preserve data between page refreshes
- Clear session on successful registration or cancellation

### 2.2 Payment Submission Screen

**URL:** `/tournaments/<slug>/payment` or `/registrations/<id>/payment`

**Layout: Split-screen (Desktop) / Stacked (Mobile)**

**Left Panel: Payment Instructions**
- Amount to pay (large, bold: ৳500)
- Accepted methods: Visual cards with logos
- **DeltaCoin Option:**
  - Display balance: "Your balance: 1,250 DC"
  - Auto-deduct: "Pay with DeltaCoin (500 DC)"
  - If insufficient: "Earn more DC or use cash payment"
- **Cash Methods:**
  - bKash: 01712345678 [Copy button]
  - Nagad: 01812345678 [Copy button]
  - Rocket: 01912345678 [Copy button]
  - Bank: Account details with copy buttons
- Deadline countdown: "Submit within 48 hours"
- Help section: FAQ, contact organizer

**Right Panel: Payment Form**
1. **Payment Method*** (radio cards)
   - DeltaCoin | bKash | Nagad | Rocket | Bank Transfer
   - Selected state: Blue border + checkmark

2. **Transaction ID*** (text input) - Hidden if DeltaCoin
   - Placeholder: "Enter transaction/reference ID"
   - Validation: Min 6 characters, alphanumeric

3. **Amount Paid*** (number input) - Hidden if DeltaCoin
   - Pre-filled with entry fee amount
   - Validation: Must match exactly (error on mismatch)

4. **Payment Screenshot*** (file upload) - Hidden if DeltaCoin
   - Drag-and-drop or click to browse
   - Supported: JPG, PNG, PDF (max 5MB)
   - Preview after upload with zoom
   - Requirements overlay: "Must show transaction ID, amount, date"

5. **Additional Notes** (textarea, optional)
   - Character limit: 500
   - Placeholder: "Any additional information..."

**Submit Button:**
- DeltaCoin: "Confirm Payment (500 DC)" → Auto-deducts
- Cash: "Submit Payment Proof" → Uploads file
- Loading state: "Processing..." with spinner

**Validation:**
- Real-time field validation
- Amount matching error: "Amount is ৳450. Entry fee is ৳500. Please pay the full amount."
- File size error: "File is 7.2MB. Maximum is 5MB. Try compressing."
- Missing required fields: Highlight with red border + error message

### 2.3 Payment Status States

**Visual Badges:**

1. **Pending Verification** (Yellow badge):
   - Icon: 🕐
   - Text: "Pending Verification"
   - Message: "Your payment proof has been submitted. Organizers usually verify within 24 hours."
   - Actions: Edit Submission, Cancel Registration, Contact Organizer

2. **Verified** (Green badge):
   - Icon: ✓
   - Text: "Payment Verified"
   - Confetti animation on first view
   - Message: "Your payment has been approved. You're all set!"
   - Display: Verified by [Organizer Name], Verified on [Date]
   - Next steps: Check-in information

3. **Rejected** (Red badge):
   - Icon: ✗
   - Text: "Payment Rejected"
   - Alert box: Rejection reason from organizer
   - Example: "Screenshot unclear - amount not visible"
   - Actions: Resubmit Payment, Contact Organizer

4. **Fee Waived** (Gold badge):
   - Icon: 🎉
   - Text: "Fee Waived"
   - Message: "Entry fee waived by organizer - You're a featured participant!"
   - Reason: "Top-ranked team" / "Sponsor invitation"

5. **Expired** (Gray badge):
   - Icon: ⏰
   - Text: "Payment Expired"
   - Warning: "Payment deadline passed. Your registration has been cancelled."
   - Actions: Contact Organizer (request extension), Re-register (if still open)

6. **Refunded** (Purple badge):
   - Icon: ↩️
   - Text: "Refunded"
   - Message: "Your payment has been refunded to [Method]"
   - Display: Refund amount, refund date, reason

### 2.4 Confirmation Screen

**URL:** `/tournaments/<slug>/registered` or `/registrations/<id>/confirmation`

**Success Hero:**
- Large checkmark icon with green glow
- Confetti animation (2 seconds, canvas-confetti)
- Heading: "Registration Successful!" or "Registration Received!" (if payment pending)

**Status Card:**
- Registration ID: REG-12345 [Copy button]
- Tournament: [Name] (link)
- Team/Player: [Name]
- Status: Badge (Pending Payment / Confirmed / Waitlisted)
- Registration Date: Nov 3, 2025 10:30 AM
- Entry Fee: ৳500 (with payment link if not paid)

**Next Steps Cards (3-column on desktop, stacked on mobile):**

1. **Complete Payment** (if applicable)
   - Icon: 💳
   - Title: "Submit Payment Proof"
   - Description: "Upload your payment screenshot to confirm your spot"
   - Deadline: "Within 48 hours"
   - Button: "Submit Payment" (primary)

2. **Check-In**
   - Icon: ✅
   - Title: "Check-In Required"
   - Description: "Check in 30 minutes before tournament start"
   - Time: "Dec 15, 2025 - 9:30 AM BST"
   - Button: "Set Reminder"

3. **Prepare**
   - Icon: 🎮
   - Title: "Get Ready to Play"
   - Description: "Join tournament Discord and review rules"
   - Button: "Join Discord"

**Quick Actions:**
- View Tournament Details (secondary button)
- Add to Calendar (dropdown: Google Calendar, Outlook, iCal)
- Share with Team (dropdown: Copy link, WhatsApp, Discord)

**Important Information Card (info alert):**
- Check-in window: Dec 15, 2025 - 9:30 AM to 10:00 AM
- Tournament Discord: [Join Server] button (mandatory)
- Tournament Rules: [Read Full Rules] link
- Contact Organizer: [Message] button

**Email Confirmation:**
- Subject: "Registration confirmed - [Tournament Name]"
- Contains: Registration details, important dates, payment instructions
- Attachments: Calendar event (.ics), Rules PDF

---

## 3. Admin Payment Verification

### 3.1 Payment Verification Dashboard

**URL:** `/organizer/tournaments/<slug>/payments`

**Access:** Tournament organizer and admins only

**Filter Options:**
- Status: All / Pending / Submitted / Verified / Rejected
- Payment Method: All / bKash / Nagad / Rocket / Bank / DeltaCoin
- Date Range: Custom date picker
- Search: By participant name, transaction ID, reference number

**Table Columns:**
1. Participant (with avatar)
2. Registration Date
3. Payment Method (badge)
4. Amount
5. Transaction ID
6. Status (colored badge)
7. Submitted Date
8. Actions (dropdown)

**Payment Card Details (expandable or modal):**
- Participant Information:
  - Name, email, phone
  - Team name (if team tournament)
- Payment Details:
  - Method, amount, currency
  - Transaction ID
  - Reference number
  - User notes
- Payment Proof:
  - Zoomable image viewer
  - Download original file
  - File size and type
- Verification History:
  - Previous rejections (if any)
  - Resubmission count
- Actions:
  - Verify Payment (green button)
  - Reject Payment (red button, opens rejection modal)
  - Contact Participant (opens message dialog)
  - View Full Registration (link to registration details)

**Bulk Actions:**
- Select multiple pending payments (checkboxes)
- Bulk Verify Selected (confirmation dialog)
- Bulk Reject Selected (requires rejection reason)

**Rejection Modal:**
- Reason dropdown:
  - Screenshot unclear - amount not visible
  - Screenshot unclear - transaction ID not visible
  - Wrong transaction ID
  - Wrong amount
  - Other (requires text explanation)
- Additional notes (textarea)
- Checkbox: "Allow resubmission" (default: checked)
- Submit button: "Reject Payment"
- Participant is notified immediately via email and in-app notification

### 3.2 Payment Verification Workflow

**Step-by-Step Process:**

1. **Participant Submits Payment:**
   - Upload payment proof screenshot/PDF
   - Enter transaction ID and reference number
   - Payment status: `pending` → `submitted`
   - Registration status: `pending` → `payment_submitted`
   - Organizer receives notification

2. **Organizer Reviews:**
   - View payment details in dashboard
   - Check screenshot for:
     - Transaction ID matches submitted ID
     - Amount matches entry fee
     - Payment date is recent
     - Screenshot is clear and readable
   - Cross-reference with payment provider if needed

3. **Organizer Verifies (Approval Path):**
   - Click "Verify Payment" button
   - Optionally add admin notes
   - Payment status: `submitted` → `verified`
   - Registration status: `payment_submitted` → `confirmed`
   - Payment timestamp: `verified_at` = now, `verified_by` = organizer
   - Participant receives confirmation email and notification
   - Participant slot assigned if not already assigned

4. **Organizer Rejects (Rejection Path):**
   - Click "Reject Payment" button
   - Select rejection reason from dropdown
   - Add additional notes (required for "Other" reason)
   - Payment status: `submitted` → `rejected`
   - Registration status: `payment_submitted` → `pending`
   - Participant receives rejection email with reason
   - Participant can resubmit corrected proof

5. **Resubmission (if rejected):**
   - Participant clicks "Resubmit Payment" button
   - Previous proof file is replaced (old file deleted)
   - New proof uploaded
   - Payment status: `rejected` → `submitted`
   - Organizer notified of resubmission
   - Process repeats from step 2

**Audit Trail:**
- All verification actions logged in database
- Includes: timestamp, admin user, action (verify/reject), notes
- Accessible in admin panel for compliance
- Exportable as CSV for records

---

## 4. Advanced Features

### 4.1 Auto-Fill Registration Data

**Source:** User profile (`apps.user_profile`)

**Auto-filled Fields:**
- Full Name: `user.get_full_name()` or `user.username`
- Email: `user.email`
- Discord ID: `profile.discord_id`
- In-Game IDs:
  - Valorant: `profile.riot_id`
  - eFootball: `profile.konami_id`
  - PUBG Mobile: `profile.pubg_mobile_id`
  - Free Fire: `profile.free_fire_id`
  - Mobile Legends: `profile.mlbb_id`
  - CS2: `profile.steam_id`
  - Dota 2: `profile.steam_id`
  - EA Sports FC: `profile.ea_id`

**Fallback:**
- If user data incomplete, allow manual entry
- Show hint: "Update your profile to auto-fill next time"
- Link to profile edit page

### 4.2 Team Registration

**Team Selection:**
- Fetch user's teams from `apps.teams.Team.objects.filter(members__user=request.user, game=tournament.game)`
- Filter by game matching tournament game
- Display team card with:
  - Team name and logo
  - Member count
  - Captain badge (if user is captain)
- Validate:
  - User has permission to register team (captain/manager/admin role)
  - Team size matches tournament requirements
  - No team member already registered in another team

**Team Roster Verification:**
- Display all team members with avatars
- Check if each member has required game ID in profile
- Warn if member already registered in another team for same tournament
- Confirm captain authorization

### 4.3 Waitlist Management

**When Tournament Full:**
- Registration status: `pending` → `waitlisted` (new status)
- Participant added to waitlist queue (FIFO order)
- Display: "You're on the waitlist (Position #5)"
- Email notification when spot opens

**Auto-Promotion:**
- When a confirmed participant cancels or is removed:
  - Find first waitlisted registration
  - Update status: `waitlisted` → `pending`
  - Send notification: "A spot has opened! Complete your registration within 24 hours."
  - If participant doesn't complete payment within deadline, move to next in waitlist

### 4.4 Fee Waivers for Top Teams

**Organizer Configuration:**
- Tournament setting: `enable_fee_waiver = True`
- Setting: `fee_waiver_top_n_teams = 3` (waive for top 3 ranked teams)

**Auto-Application:**
- When team registers:
  - Check team ranking from `apps.teams.ranking_service.get_team_rank(team_id)`
  - If rank ≤ top N threshold:
    - Create Payment record with status: `waived` (new status)
    - Registration status: `confirmed` immediately (skip payment)
    - Display gold badge: "🎉 Entry Fee Waived - Top Ranked Team!"
    - Notification: "Congratulations! Entry fee waived for top-ranked team."

**Rationale:**
- Incentivizes elite participation
- Boosts tournament prestige
- Reduces organizer workload for high-profile teams

### 4.5 Custom Field System

**Organizer Configuration:**
- Create custom fields during tournament setup
- Field properties:
  - `field_name`: Display label
  - `field_key`: Unique identifier (slug)
  - `field_type`: text | number | media | toggle | date | url | dropdown
  - `field_config`: Validation rules (min_length, max_length, options, allowed_extensions)
  - `is_required`: Boolean
  - `help_text`: Instructions for participants
  - `order`: Display order (integer)

**Dynamic Rendering:**
- Frontend renders fields based on `field_type`
- Applies validation from `field_config`
- Stores values in `registration.registration_data['custom_fields']` (JSONB)

**Examples:**
```json
{
  "field_name": "Riot ID",
  "field_key": "riot_id",
  "field_type": "text",
  "field_config": {
    "min_length": 5,
    "max_length": 50,
    "pattern": "^[a-zA-Z0-9]+#[a-zA-Z0-9]+$"
  },
  "is_required": true,
  "help_text": "Enter your Riot ID in format: PlayerName#TAG",
  "order": 1
}
```

---

## 5. Mobile Optimization

### 5.1 Responsive Design Breakpoints

- **Mobile:** < 768px (single column, stacked layout)
- **Tablet:** 768px - 1024px (2 columns where appropriate)
- **Desktop:** > 1024px (full layout with sidebars)

### 5.2 Mobile-Specific Features

**Registration Wizard:**
- Bottom navigation bar with step indicators
- Sticky "Next" button at bottom
- Touch-friendly form inputs (large touch targets, min 44x44px)
- Pull-to-refresh not needed (step-based navigation)
- Auto-scroll to first error on validation failure

**Payment Submission:**
- Camera access for payment proof upload (mobile only)
- Copy-to-clipboard buttons for payment numbers
- Large, thumb-friendly radio buttons for payment method
- Inline preview of uploaded image (tap to zoom fullscreen)
- Bottom sheet modals instead of center modals

**Status Tracking:**
- Push notifications for payment status changes (browser push API)
- Home screen badge counter for pending actions
- Swipe gestures for navigating between steps (optional)

### 5.3 Performance Targets

- First Contentful Paint: < 1.5s on 3G
- Time to Interactive: < 3.0s
- Lighthouse Performance Score: > 90
- Lighthouse Accessibility Score: 100 (WCAG 2.1 AA)

---

## 6. Integration Points

### 6.1 Existing Apps

**apps.user_profile:**
- Fetch user profile data for auto-fill
- Update profile with missing game IDs (prompt user)

**apps.teams:**
- Fetch user's teams filtered by game
- Validate team membership and captain permissions
- Get team roster for display
- Update team ranking after tournament

**apps.economy (future):**
- Check DeltaCoin balance
- Deduct DeltaCoin for entry fee payment
- Award DeltaCoin prizes after tournament
- Refund DeltaCoin if tournament cancelled

**apps.notifications (future):**
- Send registration confirmation email
- Notify organizer of new payment submission
- Notify participant of payment verification/rejection
- Send check-in reminders
- Alert on waitlist promotion

### 6.2 External Services (future)

**Payment Gateways:**
- SSLCommerz (Bangladesh)
- Stripe (international)
- bKash Merchant API (automated verification)
- Nagad Merchant API

**File Storage:**
- AWS S3 or compatible (DigitalOcean Spaces, Cloudflare R2)
- Secure proof file storage with pre-signed URLs
- Automatic file cleanup for rejected/refunded payments

---

## 7. Security & Privacy

### 7.1 Security Measures

**Input Validation:**
- Sanitize all user inputs (HTML escape)
- Validate file uploads (MIME type, file size, virus scan)
- Rate limiting on registration endpoint (10 requests/hour per user)

**Access Control:**
- Organizers can only view payments for their tournaments
- Participants can only view their own payment details
- Admins can view all payments (with audit logging)

**File Security:**
- Payment proof files stored outside web root
- Serve files via Django view with permission checks
- File naming: hashed filenames (prevent enumeration)
- Automatic file deletion after 90 days (configurable)

**Audit Logging:**
- Log all payment verification actions
- Include: timestamp, admin user, action, payment ID, tournament ID
- Exportable for compliance (GDPR, tax records)

### 7.2 Privacy Considerations

**Data Minimization:**
- Only collect necessary data
- Don't store full card numbers (use payment gateway tokens)
- Delete payment proofs after tournament conclusion (configurable retention)

**GDPR Compliance:**
- Right to access: API endpoint for users to download their data
- Right to erasure: Soft delete with anonymization option
- Right to portability: Export registration data as JSON
- Consent tracking: Store consent timestamp and IP

---

## 8. Testing Requirements

### 8.1 Unit Tests

**Models:**
- Registration status transitions
- Payment verification workflow
- Soft delete behavior
- JSONB data storage and retrieval

**Services:**
- `register_participant()` with various inputs
- `submit_payment_proof()` with file validation
- `verify_payment()` and `reject_payment()` workflows
- Edge cases: duplicate registration, full tournament, waitlist

### 8.2 Integration Tests

**Complete Workflow:**
1. User registers for tournament
2. User submits payment proof
3. Organizer verifies payment
4. Registration confirmed
5. User checks in
6. Bracket slot assigned

**Error Paths:**
1. Duplicate registration attempt
2. Payment rejection and resubmission
3. Cancellation with refund
4. Waitlist promotion

### 8.3 UI Tests

**End-to-End (Cypress/Playwright):**
- Complete registration wizard flow
- Payment proof upload and verification
- Mobile responsive behavior
- Accessibility (keyboard navigation, screen readers)

**Visual Regression:**
- Registration wizard steps
- Payment status badges
- Confirmation screen

---

## 9. Performance Benchmarks

**Database Queries:**
- Registration listing: < 50ms (with prefetch_related)
- Payment verification: < 100ms
- Waitlist processing: < 200ms

**File Operations:**
- Payment proof upload: < 2s for 5MB file
- Image preview generation: < 500ms

**Page Load Times:**
- Registration wizard: < 2s on 3G
- Payment submission: < 1.5s

---

## 10. Deployment Checklist

**Pre-Launch:**
- [ ] All models migrated to production database
- [ ] Payment proof storage configured (S3/local)
- [ ] Email templates created and tested
- [ ] Admin panel access configured
- [ ] SSL certificate installed for payment security
- [ ] CORS settings configured for uploads
- [ ] Rate limiting configured
- [ ] Monitoring and logging set up (Sentry, DataDog)

**Post-Launch:**
- [ ] Monitor payment verification latency
- [ ] Track conversion rate (registration → payment → confirmed)
- [ ] Collect user feedback on registration UX
- [ ] Analyze dropout points in wizard
- [ ] A/B test payment method preferences

---

## 11. Future Enhancements

**Phase 2 (post-MVP):**
1. Automated payment gateway integration (bKash Merchant API)
2. Bulk import registrations from CSV
3. QR code check-in system
4. Multi-language support (Bengali + English)
5. Registration analytics dashboard
6. Referral codes and discount coupons
7. Team substitution after registration
8. Roster lock enforcement

**Phase 3 (advanced):**
1. Blockchain-verified certificates
2. NFT tournament badges
3. AI-powered fraud detection
4. Predictive waitlist management
5. Social media registration sharing
6. Twitch/YouTube integration for streamer registration

---

## Conclusion

The DeltaCrown Tournament Registration System is designed to provide a comprehensive, user-friendly, and secure platform for tournament participation. This planning specification covers all aspects from database design to UI/UX, ensuring a cohesive implementation that meets both user needs and business requirements.

**Key Success Metrics:**
- 95%+ payment verification completion rate
- < 2% registration dropout rate (wizard abandonment)
- < 5 support tickets per 100 registrations
- 90%+ user satisfaction rating (post-tournament survey)
- 100% WCAG 2.1 AA accessibility compliance

**Next Steps:**
- Review planning with stakeholders
- Prioritize features for MVP vs future phases
- Assign implementation tasks to development team
- Create detailed UI mockups in Figma
- Begin Sprint 3-4 development (registration + payment features)
