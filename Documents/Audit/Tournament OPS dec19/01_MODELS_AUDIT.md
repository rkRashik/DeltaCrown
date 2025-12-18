# Tournament Models Audit
**Date**: December 19, 2025  
**Scope**: apps/tournaments Django Models Only  
**Purpose**: Evidence-based inventory of model fields and relationships

---

## 1. Tournament Model
**File**: `apps/tournaments/models/tournament.py`

### Status/State Field
```python
status = models.CharField(
    max_length=50,
    choices=STATUS_CHOICES,
    default=DRAFT,
    db_index=True
)
```

### Status Enum Values (TextChoices)
```python
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
```

### Format Choices
```python
SINGLE_ELIM = 'single_elimination'
DOUBLE_ELIM = 'double_elimination'
ROUND_ROBIN = 'round_robin'
SWISS = 'swiss'
GROUP_PLAYOFF = 'group_playoff'

format = models.CharField(
    max_length=50,
    choices=FORMAT_CHOICES,
    default=SINGLE_ELIM
)
```

### Key Fields
- `name`: CharField(max_length=200)
- `slug`: SlugField(max_length=250, unique=True)
- `organizer`: ForeignKey('accounts.User')
- `game`: ForeignKey('Game')
- `participation_type`: CharField (TEAM/SOLO)
- `platform`: CharField (PC/MOBILE/PS5/XBOX/SWITCH)
- `mode`: CharField (ONLINE/LAN/HYBRID)
- `max_participants`: PositiveIntegerField
- `min_participants`: PositiveIntegerField

---

## 2. Registration Model
**File**: `apps/tournaments/models/registration.py`

### Status Enum Values
```python
DRAFT = 'draft'
SUBMITTED = 'submitted'
PENDING = 'pending'
AUTO_APPROVED = 'auto_approved'
NEEDS_REVIEW = 'needs_review'
PAYMENT_SUBMITTED = 'payment_submitted'
CONFIRMED = 'confirmed'
REJECTED = 'rejected'
CANCELLED = 'cancelled'
WAITLISTED = 'waitlisted'
NO_SHOW = 'no_show'

status = models.CharField(
    max_length=20,
    choices=STATUS_CHOICES,
    default=PENDING,
    db_index=True
)
```

### Payment/Verification Fields
- `registration_data`: JSONField (stores participant data)
- `completion_percentage`: DecimalField(max_digits=5, decimal_places=2)
- `current_step`: PositiveIntegerField(default=1)
- `time_spent_seconds`: IntegerField(default=0)

### Check-in Fields
- `checked_in`: BooleanField(default=False)
- `checked_in_at`: DateTimeField(null=True, blank=True)
- `checked_in_by`: ForeignKey(User, null=True, blank=True)

### Bracket Assignment Fields
- `slot_number`: IntegerField(null=True, blank=True) - Bracket position
- `seed`: IntegerField(null=True, blank=True) - Seeding for bracket generation

### Waitlist Fields
- `waitlist_position`: IntegerField(null=True, blank=True)

### Relationships
- `tournament`: ForeignKey('Tournament')
- `user`: ForeignKey('accounts.User', null=True, blank=True)
- `team_id`: IntegerField(null=True, blank=True) - External team reference

### Constraints
- Unique constraint: (tournament, user) - One registration per user per tournament
- Unique constraint: (tournament, team_id) - One registration per team per tournament
- Check constraint: Either user OR team_id must be set, not both

---

## 3. Payment Model
**File**: `apps/tournaments/models/registration.py` (same file as Registration)

### Status Enum Values
```python
PENDING = 'pending'
SUBMITTED = 'submitted'
VERIFIED = 'verified'
REJECTED = 'rejected'
REFUNDED = 'refunded'
WAIVED = 'waived'

status = models.CharField(
    max_length=20,
    choices=STATUS_CHOICES,
    default=PENDING,
    db_index=True
)
```

### Payment Method Choices
```python
BKASH = 'bkash'
NAGAD = 'nagad'
ROCKET = 'rocket'
BANK = 'bank'
DELTACOIN = 'deltacoin'

payment_method = models.CharField(
    max_length=20,
    choices=PAYMENT_METHOD_CHOICES
)
```

### Payment Proof Fields
- `payment_proof`: FileField(upload_to='payment_proofs/%Y/%m/', null=True, blank=True)
- `file_type`: CharField(max_length=10, choices=[('IMAGE', 'Image'), ('PDF', 'PDF Document')])
- `transaction_id`: CharField(max_length=200, blank=True)
- `reference_number`: CharField(max_length=100, blank=True)
- `amount`: DecimalField(max_digits=10, decimal_places=2)

### Verification Fields
- `verified_by`: ForeignKey('accounts.User', null=True, blank=True)
- `verified_at`: DateTimeField(null=True, blank=True)
- `admin_notes`: TextField(blank=True) - Verification/rejection notes

### Rejection/Revision Fields
- `resubmission_count`: IntegerField(default=0) - Tracks resubmissions after rejection
- `admin_notes`: TextField - Contains rejection reason

### Fee Waiver Fields
- `waived`: BooleanField(default=False)
- `waive_reason`: TextField(blank=True)

### Relationships
- `registration`: OneToOneField(Registration)

### Constraints
- Check: Amount must be positive
- Check: If verified, must have verified_by and verified_at

### Methods
- `verify(verified_by, admin_notes)` - Mark as verified
- `reject(rejected_by, reason)` - Reject with reason
- `refund(refunded_by, reason)` - Mark as refunded

---

## 4. PaymentVerification Model
**File**: `apps/tournaments/models/payment_verification.py`

### Status Enum Values (Alternative Payment Model)
```python
class Status(models.TextChoices):
    PENDING = "pending", "Pending"
    VERIFIED = "verified", "Verified"
    REJECTED = "rejected", "Rejected"
    REFUNDED = "refunded", "Refunded"

status = models.CharField(
    max_length=16,
    choices=Status.choices,
    default=Status.PENDING
)
```

### Payment Method Choices
```python
class Method(models.TextChoices):
    BKASH = "bkash", "bKash"
    NAGAD = "nagad", "Nagad"
    ROCKET = "rocket", "Rocket"
    BANK = "bank", "Bank Transfer"
    OTHER = "other", "Other"

method = models.CharField(
    max_length=16,
    choices=Method.choices,
    default=Method.BKASH
)
```

### Payment Proof Fields
- `payer_account_number`: CharField(max_length=32, blank=True)
- `transaction_id`: CharField(max_length=64, blank=True)
- `reference_number`: CharField(max_length=64, blank=True, null=True)
- `amount_bdt`: PositiveIntegerField(null=True, blank=True)
- `proof_image`: ImageField(upload_to="payments/proofs/", null=True, blank=True)
- `note`: CharField(max_length=255, blank=True)

### Verification/Audit Fields
- `verified_by`: ForeignKey(User, null=True, blank=True, related_name="payments_verified")
- `verified_at`: DateTimeField(null=True, blank=True)
- `rejected_by`: ForeignKey(User, null=True, blank=True, related_name="payments_rejected")
- `rejected_at`: DateTimeField(null=True, blank=True)
- `refunded_by`: ForeignKey(User, null=True, blank=True, related_name="payments_refunded")
- `refunded_at`: DateTimeField(null=True, blank=True)
- `reject_reason`: TextField(blank=True)
- `last_action_reason`: CharField(max_length=200, blank=True)

### Additional Fields
- `notes`: JSONField(default=dict, blank=True) - Structured staff notes
- `idempotency_key`: CharField(max_length=255, blank=True, null=True, unique=True)

### Relationships
- `registration`: OneToOneField("tournaments.Registration")

### Methods
- `mark_verified(user, reason)` - Set status to verified
- `mark_rejected(user, reason)` - Set status to rejected with reason

---

## 5. Match Model
**File**: `apps/tournaments/models/match.py`

### State Enum Values
```python
SCHEDULED = 'scheduled'
CHECK_IN = 'check_in'
READY = 'ready'
LIVE = 'live'
PENDING_RESULT = 'pending_result'
COMPLETED = 'completed'
DISPUTED = 'disputed'
FORFEIT = 'forfeit'
CANCELLED = 'cancelled'

state = models.CharField(
    max_length=20,
    choices=STATE_CHOICES,
    default=SCHEDULED,
    db_index=True
)
```

### Participant Fields
- `participant1_id`: PositiveIntegerField(null=True, blank=True)
- `participant1_name`: CharField(max_length=100, blank=True)
- `participant2_id`: PositiveIntegerField(null=True, blank=True)
- `participant2_name`: CharField(max_length=100, blank=True)

### Score Fields
- `participant1_score`: PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
- `participant2_score`: PositiveIntegerField(default=0, validators=[MinValueValidator(0)])

### Winner/Loser Fields
- `winner_id`: PositiveIntegerField(null=True, blank=True, db_index=True)
- `loser_id`: PositiveIntegerField(null=True, blank=True)

### Scheduling Fields
- `scheduled_time`: DateTimeField(null=True, blank=True, db_index=True)
- `check_in_deadline`: DateTimeField(null=True, blank=True)
- `started_at`: DateTimeField(null=True, blank=True)
- `completed_at`: DateTimeField(null=True, blank=True)

### Check-in Fields
- `participant1_checked_in`: BooleanField(default=False)
- `participant2_checked_in`: BooleanField(default=False)

### Match Identification
- `round_number`: PositiveIntegerField(validators=[MinValueValidator(1)])
- `match_number`: PositiveIntegerField(validators=[MinValueValidator(1)])

### Lobby/Streaming Fields
- `lobby_info`: JSONField(default=dict, blank=True) - Game-specific lobby details
- `stream_url`: URLField(max_length=200, blank=True)

### Relationships
- `tournament`: ForeignKey('tournaments.Tournament')
- `bracket`: ForeignKey('tournaments.Bracket', null=True, blank=True)

### Constraints
- Check: State must be valid
- Check: Scores must be non-negative
- Check: If COMPLETED, must have winner_id and loser_id
- Check: Round and match numbers must be positive

### Properties
- `is_both_checked_in`: Returns True if both participants checked in
- `is_ready_to_start`: Returns True if ready to start
- `has_result`: Returns True if winner determined
- `is_in_progress`: Returns True if state is LIVE or PENDING_RESULT

---

## 6. MatchResultSubmission Model
**File**: `apps/tournaments/models/result_submission.py`

### Status Enum Values
```python
STATUS_PENDING = 'pending'
STATUS_CONFIRMED = 'confirmed'
STATUS_DISPUTED = 'disputed'
STATUS_AUTO_CONFIRMED = 'auto_confirmed'
STATUS_FINALIZED = 'finalized'
STATUS_REJECTED = 'rejected'

status = models.CharField(
    max_length=20,
    choices=STATUS_CHOICES,
    default=STATUS_PENDING,
    db_index=True
)
```

### Submission Fields
- `raw_result_payload`: JSONField - Game-specific result data
- `proof_screenshot_url`: CharField(max_length=500, blank=True)
- `submitter_notes`: TextField(blank=True)
- `organizer_notes`: TextField(blank=True)

### Timestamps
- `submitted_at`: DateTimeField(auto_now_add=True)
- `confirmed_at`: DateTimeField(null=True, blank=True)
- `finalized_at`: DateTimeField(null=True, blank=True)
- `auto_confirm_deadline`: DateTimeField - submitted_at + 24 hours

### Relationships
- `match`: ForeignKey('tournaments.Match')
- `submitted_by_user`: ForeignKey('accounts.User')
- `submitted_by_team`: ForeignKey('teams.Team', null=True, blank=True)
- `confirmed_by_user`: ForeignKey('accounts.User', null=True, blank=True)

### Auto-save Logic
- Automatically sets `auto_confirm_deadline` to submitted_at + 24 hours on save

---

## 7. ResultVerificationLog Model
**File**: `apps/tournaments/models/result_submission.py` (same file)

### Step Type Enum Values
```python
STEP_SCHEMA_VALIDATION = 'schema_validation'
STEP_SCORING_CALCULATION = 'scoring_calculation'
STEP_ORGANIZER_REVIEW = 'organizer_review'
STEP_FINALIZATION = 'finalization'
STEP_OPPONENT_CONFIRM = 'opponent_confirm'
STEP_OPPONENT_DISPUTE = 'opponent_dispute'
STEP_DISPUTE_ESCALATED = 'dispute_escalated'
STEP_DISPUTE_RESOLVED = 'dispute_resolved'
```

### Status Choices
```python
STATUS_SUCCESS = 'success'
STATUS_FAILURE = 'failure'
```

**Note**: Model definition incomplete in read excerpt (lines 1-200 only).

---

## 8. Bracket Model
**File**: `apps/tournaments/models/bracket.py`

### Format Enum Values
```python
SINGLE_ELIMINATION = 'single-elimination'
DOUBLE_ELIMINATION = 'double-elimination'
ROUND_ROBIN = 'round-robin'
SWISS = 'swiss'
GROUP_STAGE = 'group-stage'

format = models.CharField(
    max_length=50,
    choices=FORMAT_CHOICES,
    default=SINGLE_ELIMINATION
)
```

### Seeding Method Choices
```python
SLOT_ORDER = 'slot-order'
RANDOM = 'random'
RANKED = 'ranked'
MANUAL = 'manual'

seeding_method = models.CharField(
    max_length=30,
    choices=SEEDING_METHOD_CHOICES,
    default=SLOT_ORDER
)
```

### Key Fields
- `total_rounds`: PositiveIntegerField(default=0)
- `total_matches`: PositiveIntegerField(default=0)
- `bracket_structure`: JSONField(default=dict, blank=True) - Tree structure metadata
- `is_finalized`: BooleanField(default=False) - Prevents regeneration when True
- `generated_at`: DateTimeField(auto_now_add=True, null=True, blank=True)

### Relationships
- `tournament`: OneToOneField('tournaments.Tournament')

### Properties
- `has_third_place_match`: Checks bracket_structure for third place match flag
- `total_participants`: Reads from bracket_structure JSONB field

### Methods
- `get_round_name(round_number)` - Returns human-readable round name from bracket_structure

---

## 9. BracketNode Model
**File**: `apps/tournaments/models/bracket.py` (same file as Bracket)

### Bracket Type Choices
```python
MAIN = 'main'
LOSERS = 'losers'
THIRD_PLACE = 'third-place'

bracket_type = models.CharField(
    max_length=50,
    default=MAIN
)
```

### Position Fields
- `position`: PositiveIntegerField - Sequential position (1-indexed)
- `round_number`: PositiveIntegerField - Round number (1 = first round)
- `match_number_in_round`: PositiveIntegerField - Match number within round

### Participant Fields (Denormalized)
- `participant1_id`: IntegerField(null=True, blank=True)
- `participant1_name`: CharField(max_length=100, blank=True)
- `participant2_id`: IntegerField(null=True, blank=True)
- `participant2_name`: CharField(max_length=100, blank=True)
- `winner_id`: IntegerField(null=True, blank=True)

### Navigation Fields (Double-Linked List)
- `parent_node`: ForeignKey('self', null=True, blank=True, related_name='children') - Next match
- `parent_slot`: PositiveSmallIntegerField(null=True, blank=True) - Slot in parent (1 or 2)
- `child1_node`: ForeignKey('self', null=True, blank=True, related_name='+') - Previous match 1
- `child2_node`: ForeignKey('self', null=True, blank=True, related_name='+') - Previous match 2

### Special Flags
- `is_bye`: BooleanField(default=False) - Bye match (auto-advance)

### Relationships
- `bracket`: ForeignKey(Bracket)
- `match`: OneToOneField('tournaments.Match', null=True, blank=True)

### Constraints
- Unique: (bracket, position)
- Check: round_number > 0
- Check: match_number_in_round > 0
- Check: parent_slot must be 1 or 2 (if set)

### Properties
- `has_both_participants`: Returns True if both participant IDs set
- `has_winner`: Returns True if winner_id set
- `is_ready_for_match`: Returns True if ready to play (not bye, both participants set)

### Methods
- `get_winner_name()` - Returns winner name based on winner_id
- `get_loser_id()` - Returns loser ID based on winner_id
- `advance_winner_to_parent()` - Advances winner to parent node's appropriate slot

---

## 10. Dispute Model (Match-Level)
**File**: `apps/tournaments/models/match.py`

### Reason Enum Values
```python
SCORE_MISMATCH = 'score_mismatch'
NO_SHOW = 'no_show'
CHEATING = 'cheating'
TECHNICAL_ISSUE = 'technical_issue'
OTHER = 'other'

reason = models.CharField(
    max_length=30,
    choices=REASON_CHOICES
)
```

### Status Enum Values
```python
OPEN = 'open'
UNDER_REVIEW = 'under_review'
RESOLVED = 'resolved'
ESCALATED = 'escalated'

status = models.CharField(
    max_length=20,
    choices=STATUS_CHOICES,
    default=OPEN,
    db_index=True
)
```

### Dispute Fields
- `description`: TextField - Detailed dispute description
- `initiated_by_id`: PositiveIntegerField - User ID who initiated

### Evidence Fields
- `evidence_screenshot`: ImageField(upload_to='disputes/evidence/', null=True, blank=True)
- `evidence_video_url`: URLField(blank=True)

### Resolution Fields
- `resolved_by_id`: PositiveIntegerField(null=True, blank=True) - User ID who resolved
- `resolution_notes`: TextField(blank=True) - Organizer/admin notes
- `final_participant1_score`: PositiveIntegerField(null=True, blank=True)
- `final_participant2_score`: PositiveIntegerField(null=True, blank=True)

### Relationships
- `match`: ForeignKey('tournaments.Match')

---

## 11. DisputeRecord Model (Result Submission-Level)
**File**: `apps/tournaments/models/dispute.py`

### Status Enum Values
```python
OPEN = 'open'
UNDER_REVIEW = 'under_review'
RESOLVED_FOR_SUBMITTER = 'resolved_for_submitter'
RESOLVED_FOR_OPPONENT = 'resolved_for_opponent'
CANCELLED = 'cancelled'
ESCALATED = 'escalated'

status = models.CharField(
    max_length=32,
    choices=STATUS_CHOICES,
    default=OPEN,
    db_index=True
)
```

### Reason Code Choices
```python
REASON_SCORE_MISMATCH = 'score_mismatch'
REASON_WRONG_WINNER = 'wrong_winner'
REASON_CHEATING_SUSPICION = 'cheating_suspicion'
REASON_INCORRECT_MAP = 'incorrect_map'
REASON_MATCH_NOT_PLAYED = 'match_not_played'
REASON_OTHER = 'other'

reason_code = models.CharField(
    max_length=32,
    choices=REASON_CHOICES,
    default=REASON_OTHER
)
```

### Dispute Fields
- `description`: TextField - Opponent's detailed description
- `resolution_notes`: TextField(blank=True) - Internal resolution notes

### Timestamps
- `opened_at`: DateTimeField(auto_now_add=True, db_index=True)
- `updated_at`: DateTimeField(auto_now=True)
- `resolved_at`: DateTimeField(null=True, blank=True, db_index=True)
- `escalated_at`: DateTimeField(null=True, blank=True)

### Relationships
- `submission`: ForeignKey('tournaments.MatchResultSubmission')
- `opened_by_user`: ForeignKey(User, related_name='opened_disputes')
- `opened_by_team`: ForeignKey('teams.Team', null=True, blank=True)
- `resolved_by_user`: ForeignKey(User, null=True, blank=True, related_name='resolved_disputes')

### Methods
- `is_open()` - Returns True if status is OPEN/UNDER_REVIEW/ESCALATED
- `is_resolved()` - Returns True if resolved or cancelled

---

## 12. DisputeEvidence Model
**File**: `apps/tournaments/models/dispute.py` (same file as DisputeRecord)

### Evidence Type Choices
```python
TYPE_SCREENSHOT = 'screenshot'
TYPE_VIDEO = 'video'
TYPE_CHAT_LOG = 'chat_log'
TYPE_OTHER = 'other'

evidence_type = models.CharField(
    max_length=32,
    choices=TYPE_CHOICES,
    default=TYPE_SCREENSHOT
)
```

### Evidence Fields
- `url`: URLField(max_length=500) - External resource URL (imgur, Discord, S3)
- `notes`: TextField(blank=True) - Context about evidence
- `created_at`: DateTimeField(auto_now_add=True)

### Relationships
- `dispute`: ForeignKey(DisputeRecord)
- `uploaded_by`: ForeignKey(User, related_name='uploaded_dispute_evidence')

---

## 13. CheckIn Model
**File**: `apps/tournaments/models/lobby.py`

### Check-in Fields
- `is_checked_in`: BooleanField(default=False)
- `checked_in_at`: DateTimeField(null=True, blank=True)
- `checked_in_by`: ForeignKey('accounts.User', null=True, blank=True) - Who performed check-in

### Forfeit Fields
- `is_forfeited`: BooleanField(default=False)
- `forfeited_at`: DateTimeField(null=True, blank=True)
- `forfeit_reason`: CharField(max_length=255, blank=True)
- `notes`: TextField(blank=True) - Admin notes

### Soft Delete
- `is_deleted`: BooleanField(default=False)

### Relationships
- `tournament`: ForeignKey('tournaments.Tournament')
- `registration`: OneToOneField('tournaments.Registration')
- `user`: ForeignKey('accounts.User', null=True, blank=True)
- `team`: ForeignKey('teams.Team', null=True, blank=True)

### Note
Either user OR team is set (matches registration pattern).

---

## 14. TournamentLobby Model
**File**: `apps/tournaments/models/lobby.py` (same file)

### Check-in Configuration Fields
- `check_in_required`: BooleanField(default=True)
- `check_in_opens_at`: DateTimeField(null=True, blank=True)
- `check_in_closes_at`: DateTimeField(null=True, blank=True)

### Lobby Configuration
- `rules_url`: URLField(blank=True)
- `discord_server_url`: URLField(blank=True)
- `is_active`: BooleanField(default=True)
- `config`: JSONField(default=dict, blank=True) - Additional settings

### Relationships
- `tournament`: OneToOneField('tournaments.Tournament', related_name='lobby')

### Properties
- `is_check_in_open`: Returns True if check-in currently open
- `check_in_status`: Returns 'not_required', 'not_open', 'closed', or 'open'
- `check_in_countdown_seconds`: Returns seconds until check-in closes

### Methods
- `get_checked_in_count()` - Count of checked-in participants
- `get_total_participants_count()` - Total confirmed registrations

---

## 15. Models NOT FOUND

### Waitlist Model
**Status**: NOT FOUND  
Searched for `class Waitlist` in apps/tournaments/models/*.py - no results.

**Evidence**: Registration model has `waitlist_position` field (IntegerField), but no dedicated Waitlist model exists.

### RescheduleRequest Model
**Status**: NOT FOUND  
Searched for `class RescheduleRequest` in apps/tournaments/models/*.py - no results.

**Evidence**: No dedicated model for match rescheduling. Reschedule functionality likely handled through:
- Match.scheduled_time field updates
- Admin notes or audit logs
- No formal request/approval workflow model

---

## Summary Statistics

**Total Models Audited**: 15 core models + 0 missing models

### Models with Status/State Enums
1. Tournament (9 states: draft → archived)
2. Registration (11 states: draft → no_show)
3. Payment (6 states: pending → waived)
4. PaymentVerification (4 states: pending → refunded)
5. Match (9 states: scheduled → cancelled)
6. MatchResultSubmission (6 states: pending → rejected)
7. Dispute (4 states: open → escalated)
8. DisputeRecord (6 states: open → escalated)

### Models with Payment/Verification
1. Payment - Full payment proof + verification workflow
2. PaymentVerification - Alternative implementation with idempotency
3. Registration - References payment via OneToOne relationship

### Models with Evidence/Proof Fields
1. Payment - payment_proof file upload
2. PaymentVerification - proof_image upload
3. Dispute - evidence_screenshot + evidence_video_url
4. DisputeEvidence - url field for external resources
5. MatchResultSubmission - proof_screenshot_url

### Models with Timestamp Tracking
All models include:
- created_at/submitted_at (creation timestamp)
- updated_at (last modification)
- Action-specific timestamps (verified_at, resolved_at, completed_at, etc.)

### Models with Soft Delete
1. Tournament (inherits SoftDeleteModel)
2. Registration (inherits SoftDeleteModel)
3. CheckIn (is_deleted field)

---

## Key Findings

### 1. Dual Payment Models
Two payment verification models exist:
- `Payment` (apps/tournaments/models/registration.py)
- `PaymentVerification` (apps/tournaments/models/payment_verification.py)

Both implement similar verification workflows but with different field names and structure.

### 2. Dual Dispute Models
Two dispute models exist:
- `Dispute` (apps/tournaments/models/match.py) - Match-level disputes
- `DisputeRecord` (apps/tournaments/models/dispute.py) - Result submission-level disputes

Different status workflows and evidence handling.

### 3. Waitlist Feature
Registration has `waitlist_position` field, but no dedicated Waitlist model. Waitlist managed through Registration status='waitlisted' + position field.

### 4. No Reschedule Model
Match rescheduling handled through Match.scheduled_time updates. No formal request/approval model exists.

### 5. State Machine Complexity
Multiple models with complex state transitions:
- Tournament: 9-state lifecycle
- Registration: 11-state workflow with payment integration
- Match: 9-state with check-in and dispute branches
- Result submissions: 6-state opponent verification flow

### 6. JSONB Usage
Heavy use of JSONField for flexibility:
- Tournament: payment methods, custom configuration
- Registration: registration_data (custom fields)
- Match: lobby_info (game-specific)
- Bracket: bracket_structure (tree metadata)
- PaymentVerification: notes (structured staff metadata)

### 7. External ID Pattern
Models use IntegerField for external references (no ForeignKey):
- Match: participant1_id, participant2_id, winner_id, loser_id
- BracketNode: participant1_id, participant2_id, winner_id
- Dispute: initiated_by_id, resolved_by_id
- Registration: team_id

Denormalized names stored alongside IDs for performance.

---

**Audit Complete**: December 19, 2025
