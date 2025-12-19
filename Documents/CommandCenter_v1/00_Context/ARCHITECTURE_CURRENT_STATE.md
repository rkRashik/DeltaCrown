# 01_ARCHITECTURE_CURRENT_STATE.md

**Audit Date:** December 19, 2025  
**Scope:** apps/tournaments architecture and view-service integration patterns  
**Reference Audits:** 
- `Documents/Audit/Tournament OPS dec19/01_MODELS_AUDIT.md`
- `Documents/Audit/Tournament OPS dec19/02_VIEWS_AND_TEMPLATES_AUDIT.md`
- `Documents/Audit/Tournament OPS dec19/03_SERVICES_AND_WORKFLOWS_AUDIT.md`
- `Documents/Audit/Tournament OPS dec19/04_VIEW_TO_SERVICE_CALLMAP.md`

---

## 1. EXECUTIVE SUMMARY

**Key Finding:** Architectural inconsistency exists between organizer and participant views.

- ✅ **Participant views** (checkin.py, lobby.py) demonstrate proper service layer adoption (89-100%)
- ❌ **Organizer views** (organizer.py, organizer_results.py, disputes_management.py) bypass service layer and manipulate ORM directly (~5% service adoption)

This creates maintenance burden, testing gaps, missing notifications/audit logs, and prevents tournament_ops integration.

---

## 2. APPLICATION ARCHITECTURE

### 2.1 High-Level Structure

```
apps/tournaments/
├── models/              # 15 Django models (Tournament, Registration, Match, etc.)
├── services/            # 38 service files (business logic layer)
│   ├── registration_service.py
│   ├── check_in_service.py
│   ├── lobby_service.py
│   ├── match_service.py
│   └── ...
├── views/               # 67 CBVs, 26+ FBVs
│   ├── organizer.py              # ❌ Direct ORM (1484 lines)
│   ├── organizer_results.py      # ❌ Direct ORM (261 lines)
│   ├── disputes_management.py    # ❌ Direct ORM (~150 lines)
│   ├── result_submission.py      # ❌ TODO comments (200 lines)
│   ├── checkin.py                # ✅ Uses CheckInService (421 lines)
│   └── lobby.py                  # ✅ Uses LobbyService (250 lines)
├── api/                 # DRF API views
└── workflows/           # 4 workflow files (bracket_generation, stage_transition, etc.)
```

### 2.2 tournament_ops Integration

**tournament_ops** is a separate Django app providing headless orchestration:
- Bracket generation algorithms
- Match scheduling
- Stage transitions
- Result processing

**Integration Pattern:**
- apps/tournaments services call tournament_ops via DTOs
- Example: `BracketService` → `BracketEngineService` (tournament_ops)
- Example: `StageTransitionService` → `StageTransitionEngineService` (tournament_ops)

**Current Status:**
- ✅ Service layer has tournament_ops integration (2 of 38 services)
- ❌ Organizer views bypass services, thus never reach tournament_ops
- ⚠️ Integration incomplete in many workflows (noted as "Workflow gap" in audit)

---

## 3. VIEW-SERVICE INTEGRATION PATTERNS

### 3.1 ✅ Gold Standard Pattern (Participant Views)

**File:** `apps/tournaments/views/checkin.py` (421 lines)  
**Service Adoption:** 8 of 8 functions use CheckInService (89% adoption)

**Example:**
```python
from apps.tournaments.services.check_in_service import CheckInService

class CheckInActionView(LoginRequiredMixin, View):
    def post(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug, is_deleted=False)
        
        # Validate via service
        can_check_in = CheckInService.can_check_in(tournament, request.user)
        if not can_check_in:
            return JsonResponse({'success': False, 'message': '...'}, status=403)
        
        # Delegate to service
        registration = CheckInService.check_in(tournament, request.user)
        
        return JsonResponse({
            'success': True,
            'checked_in_at': registration.checked_in_at.isoformat()
        })
```

**Business Logic Handled by Service:**
- Check-in window validation
- Eligibility checks (registration status, payment verification)
- Timestamp recording
- Status updates
- Audit logging
- Notifications

---

**File:** `apps/tournaments/views/lobby.py` (250 lines)  
**Service Adoption:** 4 of 4 functions use LobbyService (100% adoption)

**Example:**
```python
from apps.tournaments.services.lobby_service import LobbyService

class TournamentLobbyView(LoginRequiredMixin, View):
    def get(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)
        
        # Delegate roster aggregation to service
        roster_data = LobbyService.get_roster(tournament.id)
        
        # Delegate announcements to service
        announcements = LobbyService.get_announcements(tournament.id)
        
        context = {
            'tournament': tournament,
            'roster_data': roster_data,
            'announcements': announcements,
        }
        return render(request, self.template_name, context)
```

**Business Logic Handled by Service:**
- Roster aggregation with check-in status
- Announcement filtering and ordering
- Team membership resolution
- Real-time status calculations

---

### 3.2 ❌ Anti-Pattern (Organizer Views)

**File:** `apps/tournaments/views/organizer.py` (1484 lines)  
**Service Adoption:** 1 of 20+ functions use service layer (5% adoption)

**Example of Direct ORM Manipulation:**
```python
def approve_registration(request, tournament_id, registration_id):
    """Approve a participant registration (AJAX endpoint)."""
    registration = get_object_or_404(Registration, id=registration_id)
    
    # Direct ORM write - bypasses service layer
    registration.status = 'confirmed'
    registration.save()
    
    return JsonResponse({'success': True})
    
    # Missing business logic:
    # - Email notification to participant
    # - Audit log entry (who approved, when)
    # - Payment verification check
    # - Tournament capacity check
    # - Webhook dispatch for external integrations
```

**Consequences:**
1. No email notifications sent to participants
2. No audit trail of who approved registration
3. No tournament_ops integration
4. Business logic duplicated if approval happens elsewhere
5. Untestable (would need to mock ORM .save() in tests)

---

**File:** `apps/tournaments/views/organizer_results.py` (261 lines)  
**Service Adoption:** 0 of 4 functions use service layer (0% adoption)

**Example of Incomplete Implementation:**
```python
def confirm_match_result(request, tournament_id, match_id):
    """Confirm a participant-submitted match result."""
    match = get_object_or_404(Match, id=match_id)
    
    # TODO: Call backend API
    # POST /api/tournaments/matches/{id}/confirm-result/
    
    # Placeholder: Direct ORM write
    match.state = Match.COMPLETED
    match.save()
    
    return JsonResponse({'success': True})
    
    # Missing implementation:
    # - MatchService.confirm_result() call
    # - Bracket progression logic
    # - Participant notification
    # - tournament_ops integration
```

**Status:** All 4 result management functions have TODO comments indicating incomplete service integration.

---

**File:** `apps/tournaments/views/disputes_management.py` (~150 lines analyzed)  
**Service Adoption:** 0 of 1 view uses service layer (0% adoption)

**Pattern:**
```python
class DisputeManagementView(LoginRequiredMixin, TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.get_tournament()
        
        # Direct ORM query
        disputes = Dispute.objects.filter(
            match__tournament=tournament,
            is_deleted=False
        ).select_related('match', 'reported_by')
        
        context['disputes'] = disputes
        return context
```

**Note:** Read-only query for display is acceptable. However, dispute resolution actions (if they exist) should delegate to DisputeService.

---

**File:** `apps/tournaments/views/result_submission.py` (200 lines)  
**Service Adoption:** 0 of 2 functions use service layer (0% adoption)

**Example:**
```python
def report_dispute(request, slug, match_id):
    """Report a match dispute (AJAX endpoint)."""
    match = get_object_or_404(Match, id=match_id)
    
    reason = request.POST.get('reason', '').strip()
    description = request.POST.get('description', '').strip()
    
    # TODO: Call backend API
    # POST /api/tournaments/matches/{id}/report-dispute/
    
    # Placeholder: return success
    return JsonResponse({
        'success': True,
        'message': 'Dispute submitted successfully.'
    })
    
    # Missing implementation:
    # - DisputeService.create_dispute() call
    # - Evidence validation
    # - Organizer notification
    # - Audit logging
```

**Status:** Both result submission and dispute submission have TODO comments indicating incomplete implementation.

---

## 4. SERVICE LAYER STATUS

### 4.1 Service Files Inventory

**Total Services:** 38 files in `apps/tournaments/services/`

**Key Services:**
- `registration_service.py` - Registration approval/rejection, disqualification
- `check_in_service.py` - Check-in validation and execution (USED by checkin.py)
- `lobby_service.py` - Roster/announcements aggregation (USED by lobby.py)
- `match_service.py` - Match lifecycle management (NOT USED by organizer views)
- `bracket_service.py` - Bracket generation (integrates with tournament_ops)
- `stage_transition_service.py` - Tournament stage transitions (integrates with tournament_ops)
- `payment_service.py` - Payment verification/processing (NOT USED by organizer views)
- `dispute_service.py` - Dispute creation/resolution (NOT USED by any views)

**Service Adoption by View:**
| View File | Service Used | Adoption Rate |
|-----------|--------------|---------------|
| `checkin.py` | CheckInService | 89% (8/9 functions) |
| `lobby.py` | LobbyService | 100% (4/4 functions) |
| `organizer.py` | RegistrationService (1 function only) | ~5% (1/20+ functions) |
| `organizer_results.py` | None | 0% (0/4 functions) |
| `disputes_management.py` | None | 0% (0/1 views) |
| `result_submission.py` | None | 0% (0/2 functions) |
| `live.py` (public views) | None | 0% (read-only OK) |

---

### 4.2 Service Patterns

**Good Service Design (checkin.py pattern):**
```python
# Service handles validation
CheckInService.can_check_in(tournament, user) → bool

# Service handles business logic
CheckInService.check_in(tournament, user) → Registration
  - Validates check-in window
  - Validates registration status
  - Records timestamp
  - Updates status
  - Sends notifications
  - Logs audit trail
  - Raises ValidationError if invalid
```

**Missing Service Usage (organizer.py pattern):**
```python
# View handles validation (or skips it)
registration = get_object_or_404(Registration, id=registration_id)

# View handles business logic (incomplete)
registration.status = 'confirmed'
registration.save()

# Missing:
# - Notification emails
# - Audit logging
# - Status transition validation
# - tournament_ops integration
# - Webhook dispatch
```

---

## 5. MODEL LAYER

**Total Models:** 15 Django models

**Core Models:**
- `Tournament` - Tournament definition, status, settings
- `Registration` - Participant registrations with status enum
- `Match` - Match details, participants, scores, state
- `Bracket` - Bracket structure (JSON field)
- `TournamentLobby` - Check-in window configuration
- `CheckIn` - Check-in records
- `Dispute` - Match disputes
- `Payment` - Payment records
- `TournamentResult` - Final tournament results

**Key Enums:**
- `Tournament.Status`: DRAFT, PUBLISHED, REGISTRATION_OPEN, REGISTRATION_CLOSED, SEEDING_IN_PROGRESS, BRACKET_GENERATED, READY, IN_PROGRESS, COMPLETED, CANCELLED, ARCHIVED
- `Registration.Status`: PENDING, PAYMENT_SUBMITTED, CONFIRMED, REJECTED, WAITLISTED, CANCELLED, DISQUALIFIED
- `Match.State`: SCHEDULED, READY, LIVE, PENDING_RESULT, COMPLETED, FORFEIT, CANCELLED, DISPUTED

**JSONB Fields:**
- `Bracket.bracket_structure` - Nested bracket data
- `Match.lobby_info` - Game lobby details for participants
- `Tournament.rules` - Tournament rules and settings

---

## 6. WORKFLOW STATUS

**From 03_SERVICES_AND_WORKFLOWS_AUDIT.md:**

**Workflow Readiness:**
| Workflow | Status | Notes |
|----------|--------|-------|
| Registration | READY | RegistrationService exists but underused |
| Check-In | READY | CheckInService fully integrated in checkin.py |
| Bracket Generation | READY | BracketService integrates with tournament_ops |
| Stage Transition | READY | StageTransitionService integrates with tournament_ops |
| Match Management | PARTIAL | MatchService exists but not used by organizer views |
| Result Submission | NOT READY | TODO comments in result_submission.py |
| Dispute Resolution | NOT READY | DisputeService exists but not used by views |

---

## 7. URL ROUTING STRUCTURE

### 7.1 Organizer URLs (Command Center)

**Namespace:** `/tournaments/<slug>/organizer/`

**Current Routes:**
- `/organizer/` - Dashboard
- `/organizer/registrations/` - Registration list
- `/organizer/registrations/<id>/approve/` - Approve registration (AJAX)
- `/organizer/registrations/<id>/reject/` - Reject registration (AJAX)
- `/organizer/payments/` - Payment verification
- `/organizer/matches/` - Match management
- `/organizer/results/` - Result confirmation
- `/organizer/disputes/` - Dispute management
- `/organizer/roster/` - Roster export

**Issue:** Fragmented across multiple pages; no unified dashboard

---

### 7.2 Participant URLs (Lobby Room)

**Namespace:** `/tournaments/<slug>/lobby/` and `/tournaments/<slug>/matches/`

**Current Routes:**
- `/lobby/` - Lobby hub (check-in, roster, announcements)
- `/check-in/` - Check-in action (AJAX)
- `/roster/` - Public roster view
- `/matches/<id>/` - Match detail
- `/matches/<id>/submit-result/` - Result submission (incomplete)
- `/matches/<id>/report-dispute/` - Dispute submission (incomplete)

**Issue:** Result submission and dispute submission incomplete (TODO comments)

---

## 8. TEMPLATE STRUCTURE

**Organizer Templates:**
- `templates/tournaments/organizer/dashboard.html`
- `templates/tournaments/organizer/registrations_list.html`
- `templates/tournaments/organizer/results_list.html`
- `templates/tournaments/organizer/disputes_list.html`

**Participant Templates:**
- `templates/tournaments/lobby/hub.html` - Main lobby page
- `templates/tournaments/lobby/_checkin.html` - Check-in widget (HTMX partial)
- `templates/tournaments/public/live/match_detail.html`
- `templates/tournaments/public/live/submit_result_form.html` (incomplete)

**Frontend Stack:**
- Django template language (DTL)
- Tailwind CSS for styling
- Vanilla JavaScript for interactions
- HTMX for AJAX (used in check-in widget)
- No React, no Next.js, no build step

---

## 9. KEY FINDINGS SUMMARY

### 9.1 Architectural Inconsistencies

**Finding 1: Service Layer Bypassed by Organizer Views**
- Organizer views (organizer.py, organizer_results.py) manipulate ORM directly
- 20+ organizer functions call `.save()` instead of delegating to services
- Only 1 function (`disqualify_participant`) properly uses RegistrationService

**Finding 2: Participant Views Follow Best Practices**
- Checkin.py and lobby.py delegate 89-100% of operations to services
- Proper validation, notifications, audit logging via service layer
- These views serve as gold standard for refactoring organizer views

**Finding 3: Incomplete Implementations**
- organizer_results.py: 4 functions have TODO comments for backend API integration
- result_submission.py: 2 functions have TODO comments for service layer calls
- Multiple workflows planned but not implemented

**Finding 4: No tournament_ops Integration in Organizer Actions**
- Organizer views bypass services, thus never trigger tournament_ops workflows
- Bracket progression, stage transitions not executed when organizers manually change match results
- Integration exists in service layer but unreachable from views

---

### 9.2 Business Logic Gaps

**Operations Bypassing Service Layer:**
1. Registration approval/rejection (20+ organizer actions)
2. Payment verification/rejection
3. Check-in toggle (organizer-side)
4. Match reschedule/forfeit/cancel/score override
5. Result confirmation/rejection/override
6. Bulk operations (bulk approve, bulk reject)

**Consequences:**
- ❌ No email notifications to participants
- ❌ No audit logs (who, when, why)
- ❌ No validation of business rules
- ❌ No transaction safety (partial state updates)
- ❌ No integration with tournament_ops
- ❌ No webhook dispatch for external systems
- ❌ Duplicated logic (if same action exists elsewhere)
- ❌ Untestable (would need to mock ORM in unit tests)

---

### 9.3 Positive Patterns to Preserve

**Pattern 1: CheckInService Integration (checkin.py)**
- Service provides clear API: `can_check_in()`, `check_in()`, `get_check_in_opens_at()`
- View delegates validation and execution to service
- Service handles all business logic, notifications, logging
- ValidationError raised for invalid operations

**Pattern 2: LobbyService Integration (lobby.py)**
- Service aggregates complex data: `get_roster()`, `get_announcements()`
- View focuses on rendering, service handles queries and transformations
- Clean separation of concerns

**Pattern 3: Read-Only Direct ORM (live.py)**
- Public-facing views use direct ORM for read-only display (acceptable)
- No state mutations, so service layer not required
- Optimized queries with select_related/prefetch_related

---

## 10. REFACTORING PRIORITIES

**Critical Path for Command Center + Lobby Room v1:**

**Phase 0: Service Layer Completion (Backend)**
1. Create/enhance services:
   - `RegistrationService.approve()`, `RegistrationService.reject()`
   - `PaymentService.verify()`, `PaymentService.reject()`
   - `MatchService.reschedule()`, `MatchService.forfeit()`, `MatchService.override_score()`
   - `MatchService.confirm_result()`, `MatchService.reject_result()`
   - `DisputeService.create_dispute()`, `DisputeService.resolve_dispute()`

2. Ensure all services handle:
   - Validation (raise ValidationError)
   - Notifications (email, in-app)
   - Audit logging (who, when, what)
   - tournament_ops integration (where applicable)
   - Transaction safety (@transaction.atomic)

**Phase 1: Refactor Organizer Views (Backend)**
1. Refactor organizer.py to call services instead of ORM .save()
2. Refactor organizer_results.py to call MatchService methods
3. Maintain URL patterns (backward compatibility)
4. Add comprehensive tests for refactored views

**Phase 2: Command Center UI (Frontend)**
1. Build unified organizer dashboard with Tailwind
2. Add real-time updates via HTMX/polling
3. Consolidate fragmented pages into single-page experience

**Phase 3: Lobby Room UI (Frontend)**
1. Enhance lobby hub with real-time roster updates
2. Complete result submission flow (remove TODO comments)
3. Complete dispute submission flow (remove TODO comments)
4. Add live match updates

---

## 11. TECHNICAL DEBT ASSESSMENT

**High Priority:**
- Organizer views bypass service layer (maintenance risk, missing features)
- Incomplete result submission/dispute flows (user-facing gaps)
- No real-time updates (poor UX)

**Medium Priority:**
- Fragmented organizer UI (usability issue)
- Missing audit logs for organizer actions (compliance risk)
- No integration tests for organizer workflows

**Low Priority:**
- Template duplication (DRY violations)
- Inconsistent error handling patterns
- Missing API documentation

---

**End of Architecture Current State**
