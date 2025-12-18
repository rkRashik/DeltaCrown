# Tournament Services & Workflows Audit
**Date:** December 19, 2025  
**Scope:** Service layer in `apps/tournaments/services/`  
**Purpose:** Document service files, their responsibilities, tournament_ops integration, and workflow readiness

---

## 1. Service Files Inventory

**Base Path:** `apps/tournaments/services/`  
**Total Files:** 39 Python files (38 services + 1 README)

### 1.1 Core Service Files
1. `tournament_service.py` - Tournament CRUD and lifecycle
2. `registration_service.py` - Registration and payment workflows
3. `bracket_service.py` - Bracket generation and progression
4. `match_service.py` - Match lifecycle and result handling
5. `winner_service.py` - Winner determination and completion

### 1.2 Specialized Services
6. `payment_service.py` - DeltaCoin payment integration
7. `checkin_service.py` - Check-in operations
8. `check_in_service.py` - Alternative check-in service
9. `eligibility_service.py` - Registration eligibility checks
10. `notification_service.py` - Tournament notifications

### 1.3 Registration Support Services
11. `registration_autofill.py` - Auto-fill registration data
12. `registration_eligibility.py` - Eligibility validation
13. `registration_ux.py` - Draft saving and progress tracking

### 1.4 Bracket & Match Support
14. `bracket_generator.py` - Bracket generation algorithms
15. `bracket_editor_service.py` - Manual bracket editing
16. `stage_transition_service.py` - Multi-stage transitions
17. `group_stage_service.py` - Group stage management
18. `ranking_service.py` - Participant ranking

### 1.5 Configuration & Templates
19. `game_config_service.py` - Game-specific configurations
20. `custom_field_service.py` - Dynamic custom fields
21. `template_service.py` - Tournament templates
22. `template_marketplace.py` - Template marketplace

### 1.6 Forms & Analytics
23. `form_render_service.py` - Dynamic form rendering
24. `form_validator.py` - Form validation
25. `form_analytics.py` - Form analytics
26. `analytics_service.py` - Tournament analytics
27. `analytics.py` - Analytics utilities
28. `dashboard_service.py` - Organizer dashboard

### 1.7 Advanced Features
29. `leaderboard.py` - Leaderboard calculations
30. `lobby_service.py` - Tournament lobby
31. `payout_service.py` - Prize payouts
32. `certificate_service.py` - Certificate generation
33. `tournament_discovery_service.py` - Tournament discovery

### 1.8 Operations & Utilities
34. `bulk_operations.py` - Bulk response operations
35. `response_export.py` - Response export
36. `staff_permission_checker.py` - Permission checks
37. `registration.py` - Legacy registration helpers

### 1.9 Documentation
38. `README.md` - Service layer documentation

---

## 2. Service Responsibilities

### 2.1 TournamentService (`tournament_service.py`)
**Purpose:** Tournament CRUD, status transitions, lifecycle management

**Key Methods:**
- `create_tournament(organizer, data)` - Create with validation
- `update_tournament(tournament_id, user, data)` - Update with permissions
- `publish_tournament(tournament_id, user)` - Transition DRAFT → PUBLISHED
- `cancel_tournament(tournament_id, user, reason)` - Soft delete with refunds

**Calls tournament_ops:** ❌ No  
**Integration:** Uses `TournamentVersion` for audit trail

---

### 2.2 RegistrationService (`registration_service.py`)
**Purpose:** Registration creation, payment submission, verification, approval

**Key Methods:**
- `register_participant(tournament_id, user, team_id, registration_data)` - Create registration
- `check_eligibility(tournament, user, team_id)` - Validate eligibility
- `submit_payment(registration_id, payment_method, amount, transaction_id, payment_proof)` - Submit payment proof
- `verify_payment(payment_id, verified_by, admin_notes)` - Admin verifies payment → status=CONFIRMED
- `reject_payment(payment_id, rejected_by, reason)` - Admin rejects payment
- `pay_with_deltacoin(registration_id, user)` - DeltaCoin instant payment
- `cancel_registration(registration_id, user, reason)` - Cancel with refund

**Calls tournament_ops:** ❌ No  
**Integration:** Uses `apps.economy` for DeltaCoin, `Payment` model for verification workflow

---

### 2.3 BracketService (`bracket_service.py`)
**Purpose:** Bracket generation, seeding, winner progression

**Key Methods:**
- `generate_bracket_universal_safe(tournament_id, bracket_format, seeding_method, participants)` - Feature-flagged generation
- `generate_bracket(tournament_id, bracket_format, seeding_method)` - Legacy generation
- `generate_knockout_from_groups(stage_id, format, seeding_method)` - Generate from group standings
- `create_matches_from_bracket(bracket)` - Create Match objects from BracketNode tree
- `update_bracket_after_match(match)` - Advance winner to next round
- `get_bracket_visualization_data(bracket_id)` - Fetch bracket tree for UI

**Calls tournament_ops:** ✅ Yes  
**Integration:**
- Imports `apps.tournament_ops.services.bracket_engine_service.BracketEngineService` (line 193)
- Imports DTOs: `TournamentDTO`, `StageDTO`, `TeamDTO` (lines 194-196)
- Calls `BracketEngineService().generate_bracket()` when `BRACKETS_USE_UNIVERSAL_ENGINE=True` (line 256)
- Feature flag controlled: `settings.BRACKETS_USE_UNIVERSAL_ENGINE` (default: False for rollback safety)

---

### 2.4 MatchService (`match_service.py`)
**Purpose:** Match lifecycle, result submission, confirmation, dispute handling

**Key Methods:**
- `create_match(tournament, bracket, round_number, match_number, participant1_id, participant2_id, scheduled_time)` - Create match
- `submit_result(match, submitter_id, winner_id, participant1_score, participant2_score)` - Submit result → state=PENDING_RESULT
- `confirm_result(match, confirmed_by_id)` - Confirm result → state=COMPLETED, calls `BracketService.update_bracket_after_match()`
- `report_dispute(match, initiated_by_id, reason, description, evidence_screenshot, evidence_video_url)` - Create dispute → state=DISPUTED
- `resolve_dispute(dispute, resolved_by_id, resolution_notes, final_participant1_score, final_participant2_score)` - Resolve dispute with final scores
- `forfeit_match(match, forfeited_by_id)` - Forfeit match
- `cancel_match(match)` - Cancel match

**Calls tournament_ops:** ❌ No  
**Integration:** Calls `BracketService.update_bracket_after_match()` after result confirmation for winner progression

---

### 2.5 WinnerDeterminationService (`winner_service.py`)
**Purpose:** Tournament winner determination, completion verification, tie-breaking

**Key Methods:**
- `determine_winner()` - Main entry point: verify completion → identify placements → create TournamentResult
- `verify_tournament_completion()` - Check all matches COMPLETED, no disputes
- `_determine_placements()` - Identify winner, runner_up, third_place
- `_apply_tie_breaker()` - Head-to-head → score diff → seed → time
- `_detect_forfeit_chain(winner_reg)` - Flag forfeit chains for review

**Calls tournament_ops:** ❌ No  
**Integration:** Updates `Tournament.status → COMPLETED`, creates `TournamentResult` with audit trail

---

### 2.6 PaymentService (`payment_service.py`)
**Purpose:** DeltaCoin payment integration, instant verification

**Key Methods:**
- `get_wallet_balance(user)` - Get DeltaCoin balance
- `process_deltacoin_payment(registration_id, user, idempotency_key)` - Deduct from wallet, auto-verify, status=CONFIRMED
- Integration with `apps.economy.services` for wallet operations

**Calls tournament_ops:** ❌ No  
**Integration:** Uses `apps.economy` for DeltaCoin transactions

---

### 2.7 CheckinService (`checkin_service.py`)
**Purpose:** Participant check-in operations with timing rules

**Key Methods:**
- `check_in(registration_id, actor)` - Check in participant
- `undo_check_in(registration_id, actor, reason)` - Undo check-in (15-min window or organizer override)
- `bulk_check_in(registration_ids, actor)` - Bulk check-in for organizers
- `_validate_check_in_eligibility()` - Validate timing, status, permissions

**Calls tournament_ops:** ❌ No  
**Integration:** Updates `Registration.checked_in`, audit logging

---

### 2.8 EligibilityService (`eligibility_service.py` + `registration_eligibility.py`)
**Purpose:** Registration eligibility validation

**Key Methods:**
- `check_eligibility(tournament, user)` - Check if user can register
- Returns: `{can_register: bool, reason: str, status: str, registration: Registration|None, action_url: str, action_label: str}`
- Validates: tournament status, registration period, capacity, duplicate registration, team eligibility

**Calls tournament_ops:** ❌ No  

---

### 2.9 NotificationService (`notification_service.py`)
**Purpose:** Tournament-related notifications (email + in-app)

**Key Methods:**
- `notify_registration_confirmed(registration)` - Confirmation email
- `notify_match_scheduled(match)` - Match schedule notification
- `notify_match_starting_soon(match, minutes_before)` - Reminder notification
- `notify_match_completed(match)` - Match result notification

**Calls tournament_ops:** ❌ No  
**Integration:** Uses `apps.notifications.models.Notification`, sends emails

---

### 2.10 StageTransitionService (`stage_transition_service.py`)
**Purpose:** Multi-stage tournament transitions (group → bracket)

**Key Methods:**
- `calculate_advancement(stage_id)` - Determine advancing participants from group stage
- `generate_next_stage(current_stage_id)` - Create next stage (bracket or groups)

**Calls tournament_ops:** ✅ Yes  
**Integration:**
- Imports `apps.tournament_ops.services.bracket_engine_service.BracketEngineService` (line 400)
- Imports DTOs: `TeamDTO`, `TournamentDTO`, `StageDTO` (line 401)
- Calls `BracketEngineService().generate_bracket()` for knockout stage generation

---

### 2.11 GroupStageService (`group_stage_service.py`)
**Purpose:** Group stage management (groups, standings, matches)

**Key Methods:**
- `create_groups(stage_id, num_groups, group_size, seed_method)` - Create groups with seeding
- `generate_group_matches(stage_id)` - Generate round-robin matches
- `get_advancers(tournament_id)` - Get advancing participants from groups

**Calls tournament_ops:** ❌ No  

---

### 2.12 Other Services Summary
**Form Services:**
- `form_render_service.py` - Dynamic form rendering from JSON schema
- `form_validator.py` - Field validation with conditional logic
- `form_analytics.py` - Form analytics (completion rate, abandonment)

**Configuration Services:**
- `game_config_service.py` - Game-specific tournament rules (JSONB config)
- `custom_field_service.py` - Tournament custom fields (7 field types)
- `template_service.py` - Tournament template management

**Analytics Services:**
- `analytics_service.py` - Tournament analytics
- `dashboard_service.py` - Organizer dashboard metrics
- `leaderboard.py` - Leaderboard calculations

**Advanced Features:**
- `lobby_service.py` - Tournament lobby management
- `payout_service.py` - Prize distribution
- `certificate_service.py` - Certificate generation with QR codes
- `tournament_discovery_service.py` - Tournament browsing/filtering

**Utilities:**
- `registration_autofill.py` - Auto-fill from user profile
- `registration_ux.py` - Draft saving, progress tracking
- `bulk_operations.py` - Bulk registration operations
- `response_export.py` - CSV export
- `ranking_service.py` - Participant ranking
- `bracket_editor_service.py` - Manual bracket editing
- `bracket_generator.py` - Legacy bracket algorithms

**None of these call tournament_ops**

---

## 3. tournament_ops Integration Summary

### 3.1 Services Calling tournament_ops
**Total:** 2 services

1. **BracketService** (`bracket_service.py`)
   - Method: `generate_bracket_universal_safe()` (line 76)
   - Imports: `BracketEngineService`, `TournamentDTO`, `StageDTO`, `TeamDTO` (lines 193-196)
   - Calls: `BracketEngineService().generate_bracket()` (line 256)
   - Feature Flag: `settings.BRACKETS_USE_UNIVERSAL_ENGINE` (default: False)

2. **StageTransitionService** (`stage_transition_service.py`)
   - Method: `generate_next_stage()` (line 241)
   - Imports: `BracketEngineService`, DTOs (lines 400-401)
   - Calls: `BracketEngineService().generate_bracket()` for knockout stage

### 3.2 tournament_ops Structure
**Path:** `apps/tournament_ops/`

**Directories:**
- `adapters/` - External system adapters
- `dtos/` - Data Transfer Objects (TournamentDTO, StageDTO, TeamDTO, MatchDTO)
- `events/` - Domain events
- `services/` - Business logic services
- `tests/` - Test suite

**Key Files:**
- `services/bracket_engine_service.py` - Universal bracket generation engine
- `exceptions.py` - Custom exceptions
- `tasks_dispute.py` - Celery tasks for disputes
- `tasks_result_submission.py` - Celery tasks for results

**Integration Pattern:**
- tournament_ops is **DTO-only** (no Django model imports)
- tournaments services convert models to DTOs before calling tournament_ops
- tournament_ops returns DTOs, tournaments services convert back to models

---

## 4. Workflow Readiness Assessment

### 4.1 Registration → Verify → Approve Workflow

**Status:** ✅ **READY**

**Flow:**
1. **Registration Creation:** `RegistrationService.register_participant()` → status=PENDING
2. **Payment Submission:** `RegistrationService.submit_payment()` → status=PAYMENT_SUBMITTED
3. **Payment Verification:** `RegistrationService.verify_payment()` → status=CONFIRMED
4. **Alternative:** `PaymentService.process_deltacoin_payment()` → instant status=CONFIRMED

**Components:**
- ✅ Registration model with 11 status states (DRAFT → NO_SHOW)
- ✅ Payment model with 6 status states (PENDING → REFUNDED)
- ✅ Eligibility checks in `RegistrationService.check_eligibility()`
- ✅ DeltaCoin integration for instant payment
- ✅ Notification service for confirmation emails
- ✅ Audit logging in payment verification

**Reason:** Complete workflow with validation, payment processing, status transitions, and notifications.

---

### 4.2 Bracket Generation → Retrieval Workflow

**Status:** ✅ **READY**

**Flow:**
1. **Generation:** `BracketService.generate_bracket_universal_safe()` or `generate_bracket()`
2. **Match Creation:** `BracketService.create_matches_from_bracket()`
3. **Retrieval:** `BracketService.get_bracket_visualization_data()`

**Components:**
- ✅ Legacy bracket generation algorithms (single-elim, double-elim, round-robin)
- ✅ Universal bracket engine integration via feature flag
- ✅ tournament_ops integration for advanced bracket generation
- ✅ Bracket visualization data endpoint
- ✅ Seeding methods: slot-order, random, ranked, manual
- ✅ BracketNode tree structure for navigation

**Reason:** Dual implementation (legacy + universal) with feature flag for safe rollback, visualization support, multiple seeding strategies.

---

### 4.3 Match Result → Confirm → Advance Workflow

**Status:** ✅ **READY**

**Flow:**
1. **Result Submission:** `MatchService.submit_result()` → state=PENDING_RESULT
2. **Confirmation:** `MatchService.confirm_result()` → state=COMPLETED
3. **Winner Advancement:** `BracketService.update_bracket_after_match()` → updates BracketNode, advances winner

**Components:**
- ✅ Match model with 9 state machine states (SCHEDULED → COMPLETED)
- ✅ Result submission with scores
- ✅ Opponent confirmation workflow
- ✅ Automatic bracket progression after confirmation
- ✅ WebSocket broadcasting for real-time updates
- ✅ Winner determination service for final tournament completion

**Reason:** Complete state machine with result submission, confirmation, bracket progression, and winner determination.

---

### 4.4 Dispute → Resolution Workflow

**Status:** ✅ **READY**

**Flow:**
1. **Dispute Creation:** `MatchService.report_dispute()` → match state=DISPUTED, dispute status=OPEN
2. **Review:** Organizer reviews dispute evidence
3. **Resolution:** `MatchService.resolve_dispute()` → dispute status=RESOLVED, match updated with final scores
4. **Progression:** Winner advances via `BracketService.update_bracket_after_match()`

**Components:**
- ✅ Dispute model with 4 status states (OPEN → ESCALATED)
- ✅ DisputeRecord model with 6 status states (for result-submission-level disputes)
- ✅ DisputeEvidence model for evidence attachments
- ✅ Dispute resolution with final score override
- ✅ Audit logging in dispute resolution
- ✅ Match state transition: DISPUTED → COMPLETED
- ✅ Escalation support for complex disputes

**Reason:** Dual dispute models (match-level + result-submission-level), evidence attachments, resolution workflow with audit trail, escalation support.

---

## 5. Missing or Partial Workflows

### 5.1 Waitlist Management
**Status:** ❌ **MISSING**

**Reason:** `Registration.waitlist_position` field exists, but no dedicated Waitlist model or service methods for waitlist promotion workflow.

**Impact:** Manual waitlist management required.

---

### 5.2 Match Rescheduling
**Status:** ⚠️ **PARTIAL**

**Evidence:** No formal RescheduleRequest model found. Rescheduling handled via `Match.scheduled_time` updates in organizer views.

**Reason:** Basic rescheduling exists (update scheduled_time), but no formal request/approval workflow.

**Impact:** Organizer can reschedule, but no participant-initiated reschedule requests.

---

### 5.3 Refund Processing
**Status:** ⚠️ **PARTIAL**

**Evidence:** `Payment.refund()` method exists (line not specified), but no automated refund service for cancellations.

**Reason:** Refund method on Payment model, but `RegistrationService.cancel_registration()` may not automatically process refunds.

**Impact:** Manual refund processing may be required for cancellations.

---

### 5.4 Team Roster Validation
**Status:** ⚠️ **PARTIAL**

**Evidence:** `RegistrationService._validate_team_registration_permission()` exists, but team roster size validation not found in service layer.

**Reason:** Team permission validation exists, but no enforcement of min/max roster size during registration.

**Impact:** Invalid team sizes may be allowed.

---

## 6. Key Findings

### 6.1 Service Layer Maturity
- **38 service files** covering all major tournament operations
- **Service layer pattern** consistently applied (ADR-001 compliance)
- **Transaction safety** with `@transaction.atomic` decorators
- **Audit logging** in critical operations (payment verification, dispute resolution)
- **WebSocket integration** for real-time updates (Module 2.3)

### 6.2 tournament_ops Integration
- **2 services** integrate with tournament_ops: `BracketService`, `StageTransitionService`
- **Feature flag** controls universal bracket engine usage (`BRACKETS_USE_UNIVERSAL_ENGINE`)
- **DTO pattern** used for clean separation (no model imports in tournament_ops)
- **Rollback safety** with dual implementation (legacy + universal)

### 6.3 Workflow Completeness
- ✅ **Registration workflow:** Complete with payment verification and DeltaCoin integration
- ✅ **Bracket workflow:** Complete with dual implementation and visualization
- ✅ **Match result workflow:** Complete with state machine and progression
- ✅ **Dispute workflow:** Complete with dual models and escalation
- ⚠️ **Waitlist workflow:** Missing dedicated service
- ⚠️ **Reschedule workflow:** Partial (no formal request model)
- ⚠️ **Refund workflow:** Partial (manual processing may be required)

### 6.4 Code Quality Indicators
- **Type hints** used in most services
- **Docstrings** with Google-style formatting
- **Validation** at service layer (not in views)
- **Error handling** with `ValidationError` and custom exceptions
- **Logging** for debugging and audit trails
- **Integration points** clearly documented in docstrings

---

## 7. Summary Statistics

| Metric | Count |
|--------|-------|
| **Total Service Files** | 38 |
| **Services Calling tournament_ops** | 2 |
| **Core Workflows** | 4 |
| **Ready Workflows** | 4 |
| **Partial Workflows** | 4 |
| **Missing Workflows** | 0 major (1 minor: waitlist) |
| **Lines of Code (estimated)** | ~15,000+ |

---

## 8. Recommendations

### 8.1 High Priority
1. **Enable universal bracket engine** after thorough testing (feature flag ready)
2. **Document refund workflow** for registration cancellations
3. **Create WaitlistService** for formal waitlist management

### 8.2 Medium Priority
4. **Create RescheduleRequestService** for participant-initiated rescheduling
5. **Add team roster size validation** in RegistrationService
6. **Centralize audit logging** (currently ad-hoc in services)

### 8.3 Low Priority
7. **Consolidate check-in services** (checkin_service.py vs check_in_service.py duplication)
8. **Retire legacy registration helpers** (registration.py if unused)

---

**End of Services & Workflows Audit**
