# 04_VIEW_TO_SERVICE_CALLMAP.md

**Audit Date:** December 19, 2024  
**Scope:** apps/tournaments/views/  
**Purpose:** Map important tournament views to service layer methods they call

---

## Executive Summary

**Pattern Discovered:** Most organizer console views bypass the service layer and manipulate Django ORM directly. Only ~5% of organizer actions properly delegate to service methods.

**Service Layer Adoption:**
- ✅ **CheckInService**: Full adoption in checkin.py (8/8 functions use service)
- ✅ **LobbyService**: Full adoption in lobby.py (4/4 functions use service)
- ⚠️ **RegistrationService**: Partial adoption in organizer.py (1/20+ functions use service)
- ❌ **MatchService**: Zero adoption in organizer_results.py (0/4 functions use service - TODO comments only)
- ❌ **DisputeService**: Not used in disputes_management.py (direct ORM queries)
- ❌ **Service Layer**: Not used in live.py or result_submission.py (direct ORM queries)

**Key Findings:**
1. **Architectural Inconsistency**: Participant-facing views (checkin, lobby) properly use service layer, but organizer views (organizer.py, organizer_results.py) bypass it
2. **Direct ORM Pattern**: 20+ organizer functions manipulate models directly with `.save()`, `.update()`, `.filter()`
3. **Incomplete Backend Integration**: Multiple TODO comments indicate planned service integration not yet implemented
4. **Single Service Call**: Only `disqualify_participant()` in organizer.py calls `RegistrationService.disqualify_registration()`

---

## 1. ORGANIZER CONSOLE VIEWS

**File:** `apps/tournaments/views/organizer.py` (1484 lines)  
**Pattern:** Direct ORM manipulation (95% of functions)  
**Service Adoption:** 1 of 20+ functions use service layer

### 1.1 Dashboard & Overview Views

#### OrganizerDashboardView.get_context_data()
- **Service Calls:** None
- **ORM Usage:** `calls ORM directly`
- **Evidence:**
  ```python
  tournaments = Tournament.objects.filter(
      organizer=request.user
  ).annotate(
      registration_count=Count('registrations')
  )
  ```

#### OrganizerTournamentDetailView.get_context_data()
- **Service Calls:** None
- **ORM Usage:** `calls ORM directly`
- **Evidence:** Multiple direct queries:
  - `registrations.filter(is_deleted=False)`
  - `matches.filter(is_deleted=False)`
  - `payments.filter(is_deleted=False)`
  - `disputes.filter(is_deleted=False)`

#### OrganizerHubView.get_context_data()
- **Service Calls:** None
- **ORM Usage:** `calls ORM directly`
- **Evidence:** Direct aggregation queries for stats

---

### 1.2 Registration Management Actions

#### approve_registration(request, tournament_id, registration_id)
- **Service Calls:** None
- **ORM Usage:** `calls ORM directly`
- **Evidence:**
  ```python
  registration = get_object_or_404(Registration, id=registration_id)
  registration.status = 'confirmed'
  registration.save()
  ```
- **Business Logic Bypassed:** Email notifications, audit logging, status transitions

#### reject_registration(request, tournament_id, registration_id)
- **Service Calls:** None
- **ORM Usage:** `calls ORM directly`
- **Evidence:**
  ```python
  registration.status = 'rejected'
  registration.save()
  ```
- **Business Logic Bypassed:** Refund processing, notification emails, audit logging

#### bulk_approve_registrations(request, tournament_id)
- **Service Calls:** None
- **ORM Usage:** `calls ORM directly`
- **Evidence:**
  ```python
  Registration.objects.filter(
      tournament=tournament,
      id__in=registration_ids
  ).update(status=Registration.CONFIRMED)
  ```
- **Business Logic Bypassed:** Bulk email notifications, audit logging, transaction safety

#### bulk_reject_registrations(request, tournament_id)
- **Service Calls:** None
- **ORM Usage:** `calls ORM directly`
- **Evidence:**
  ```python
  for reg in registrations:
      reg.status = Registration.REJECTED
      reg.save()
  ```
- **Business Logic Bypassed:** Bulk refunds, notification emails

#### disqualify_participant(request, tournament_id, registration_id) ✅
- **Service Calls:** `calls RegistrationService.disqualify_registration()`
- **Evidence:**
  ```python
  from apps.tournaments.services.registration_service import RegistrationService
  
  RegistrationService.disqualify_registration(
      registration=registration,
      reason=reason,
      disqualified_by=request.user
  )
  ```
- **Notes:** This is the ONLY organizer function that properly delegates to service layer
- **Business Logic Included:** Audit logging, notification emails, status transitions

---

### 1.3 Payment Management Actions

#### verify_payment(request, tournament_id, payment_id)
- **Service Calls:** None
- **ORM Usage:** `calls ORM directly`
- **Evidence:**
  ```python
  payment = get_object_or_404(Payment, id=payment_id)
  payment.status = 'verified'
  payment.save()
  ```
- **Business Logic Bypassed:** Payment processing, receipt generation, notification emails

#### reject_payment(request, tournament_id, payment_id)
- **Service Calls:** None
- **ORM Usage:** `calls ORM directly`
- **Evidence:**
  ```python
  payment.status = 'rejected'
  payment.save()
  ```
- **Business Logic Bypassed:** Refund processing, notification emails, audit logging

---

### 1.4 Check-In Management

#### toggle_checkin(request, tournament_id, registration_id)
- **Service Calls:** None
- **ORM Usage:** `calls ORM directly`
- **Evidence:**
  ```python
  registration.checked_in = not registration.checked_in
  if registration.checked_in:
      registration.checked_in_at = timezone.now()
  registration.save()
  ```
- **Business Logic Bypassed:** Check-in window validation, audit logging
- **Note:** Should use CheckInService (which has proper validation logic)

---

### 1.5 Match Management Actions

#### reschedule_match(request, tournament_id, match_id)
- **Service Calls:** None
- **ORM Usage:** `calls ORM directly`
- **Evidence:**
  ```python
  match = get_object_or_404(Match, id=match_id)
  match.scheduled_time = new_scheduled_time
  match.save()
  ```
- **Business Logic Bypassed:** Participant notifications, bracket validation, conflict detection

#### forfeit_match(request, tournament_id, match_id)
- **Service Calls:** None
- **ORM Usage:** `calls ORM directly`
- **Evidence:**
  ```python
  match.state = Match.FORFEIT
  match.winner_id = winner_id
  match.save()
  ```
- **Business Logic Bypassed:** Bracket progression, notification emails, audit logging

#### override_match_score(request, tournament_id, match_id)
- **Service Calls:** None
- **ORM Usage:** `calls ORM directly`
- **Evidence:**
  ```python
  match.participant1_score = new_participant1_score
  match.participant2_score = new_participant2_score
  match.winner_id = winner_id
  match.state = Match.COMPLETED
  match.save()
  ```
- **Business Logic Bypassed:** Bracket progression, dispute resolution, notification emails

#### cancel_match(request, tournament_id, match_id)
- **Service Calls:** None
- **ORM Usage:** `calls ORM directly`
- **Evidence:**
  ```python
  match.state = Match.CANCELLED
  match.save()
  ```
- **Business Logic Bypassed:** Bracket validation, participant notifications

---

### 1.6 Export Functions

#### export_roster_csv(request, tournament_id)
- **Service Calls:** None
- **ORM Usage:** `calls ORM directly`
- **Evidence:**
  ```python
  registrations = Registration.objects.filter(
      tournament=tournament,
      is_deleted=False
  ).select_related('user')
  ```

#### export_payments_csv(request, tournament_id)
- **Service Calls:** None
- **ORM Usage:** `calls ORM directly`
- **Evidence:** Direct query for Payment objects

---

## 2. ORGANIZER RESULTS MANAGEMENT

**File:** `apps/tournaments/views/organizer_results.py` (261 lines)  
**Pattern:** TODO comments for backend API integration (0% implemented)  
**Service Adoption:** 0 of 4 functions use service layer

### 2.1 Results Views

#### PendingResultsView.get_queryset()
- **Service Calls:** None
- **ORM Usage:** `calls ORM directly`
- **Evidence:**
  ```python
  return Match.objects.filter(
      tournament=tournament,
      state=Match.PENDING_RESULT,
      is_deleted=False
  )
  ```

---

### 2.2 Results Actions

#### confirm_match_result(request, tournament_id, match_id)
- **Service Calls:** None (TODO comment indicates planned)
- **ORM Usage:** `calls ORM directly` (incomplete implementation)
- **Evidence:**
  ```python
  # TODO: Call backend API
  # POST /api/tournaments/matches/{id}/confirm-result/
  ```
- **Status:** Backend integration not yet implemented
- **Business Logic Missing:** Result confirmation, bracket progression, notifications

#### reject_match_result(request, tournament_id, match_id)
- **Service Calls:** None (TODO comment indicates planned)
- **ORM Usage:** `calls ORM directly` (incomplete implementation)
- **Evidence:**
  ```python
  # TODO: Implement rejection logic
  ```
- **Status:** Not implemented
- **Business Logic Missing:** Result rejection, dispute creation, notifications

#### override_match_result(request, tournament_id, match_id)
- **Service Calls:** None (TODO comment indicates planned)
- **ORM Usage:** `calls ORM directly` (incomplete implementation)
- **Evidence:**
  ```python
  # TODO: Call backend API or use MatchService
  ```
- **Status:** Backend integration not yet implemented
- **Business Logic Missing:** Manual result override, bracket progression, audit logging

---

## 3. DISPUTE MANAGEMENT

**File:** `apps/tournaments/views/disputes_management.py` (~150 lines analyzed)  
**Pattern:** Direct ORM filtering (no service layer)  
**Service Adoption:** 0 of 1 view uses service layer

### 3.1 Dispute Views

#### DisputeManagementView.get_context_data()
- **Service Calls:** None
- **ORM Usage:** `calls ORM directly`
- **Evidence:**
  ```python
  disputes = Dispute.objects.filter(
      match__tournament=tournament,
      is_deleted=False
  ).select_related(
      'match',
      'reported_by',
      'match__tournament'
  )
  ```
- **Notes:** Query building and filtering only, no business logic service calls

---

## 4. CHECK-IN VIEWS (Participant-Facing)

**File:** `apps/tournaments/views/checkin.py` (421 lines)  
**Pattern:** ✅ Full service layer adoption  
**Service Adoption:** 8 of 8 functions use CheckInService

### 4.1 Check-In Views

#### TournamentLobbyView.get_context_data()
- **Service Calls:** `calls CheckInService` (4 method calls)
- **Evidence:**
  ```python
  from apps.tournaments.services.check_in_service import CheckInService
  
  context['check_in_window'] = {
      'opens_at': CheckInService.get_check_in_opens_at(tournament),
      'closes_at': CheckInService.get_check_in_closes_at(tournament),
      'is_open': CheckInService.is_check_in_window_open(tournament),
      'can_check_in': CheckInService.can_check_in(tournament, request.user),
  }
  ```
- **Business Logic Delegated:** Check-in window validation, eligibility checks

---

### 4.2 Check-In Actions

#### CheckInActionView.post()
- **Service Calls:** `calls CheckInService.check_in()`
- **Evidence:**
  ```python
  registration = CheckInService.check_in(tournament, request.user)
  ```
- **Business Logic Delegated:** Check-in validation, timestamp recording, status updates

#### CheckInActionView._get_error_message()
- **Service Calls:** `calls CheckInService` (3 method calls)
- **Evidence:**
  ```python
  CheckInService.is_check_in_window_open(tournament)
  CheckInService.get_check_in_opens_at(tournament)
  CheckInService.get_check_in_closes_at(tournament)
  ```

#### CheckInStatusView.get()
- **Service Calls:** `calls CheckInService` (4 method calls)
- **Evidence:**
  ```python
  check_in_window = {
      'opens_at': CheckInService.get_check_in_opens_at(tournament),
      'closes_at': CheckInService.get_check_in_closes_at(tournament),
      'is_open': CheckInService.is_check_in_window_open(tournament),
      'can_check_in': CheckInService.can_check_in(tournament, request.user),
  }
  ```

#### RosterView.get()
- **Service Calls:** None
- **ORM Usage:** `calls ORM directly`
- **Evidence:**
  ```python
  roster = Registration.objects.filter(
      tournament=tournament,
      is_deleted=False
  )
  ```
- **Notes:** Read-only roster query (acceptable pattern for display-only views)

---

## 5. LOBBY VIEWS (Participant-Facing)

**File:** `apps/tournaments/views/lobby.py` (250 lines)  
**Pattern:** ✅ Full service layer adoption  
**Service Adoption:** 4 of 4 functions use LobbyService

### 5.1 Lobby Views

#### TournamentLobbyView.get()
- **Service Calls:** `calls LobbyService` (2 method calls)
- **Evidence:**
  ```python
  from apps.tournaments.services.lobby_service import LobbyService
  
  roster_data = LobbyService.get_roster(tournament.id)
  announcements = LobbyService.get_announcements(tournament.id)
  ```
- **Business Logic Delegated:** Roster aggregation, announcement retrieval

---

### 5.2 Lobby Actions

#### CheckInView.post()
- **Service Calls:** `calls LobbyService.perform_check_in()`
- **Evidence:**
  ```python
  check_in = LobbyService.perform_check_in(
      tournament_id=tournament.id,
      user_id=request.user.id,
      team_id=team_id
  )
  ```
- **Business Logic Delegated:** Check-in validation, team handling, timestamp recording

#### LobbyRosterAPIView.get()
- **Service Calls:** `calls LobbyService.get_roster()`
- **Evidence:**
  ```python
  roster_data = LobbyService.get_roster(tournament.id)
  ```

#### LobbyAnnouncementsAPIView.get()
- **Service Calls:** `calls LobbyService.get_announcements()`
- **Evidence:**
  ```python
  announcements = LobbyService.get_announcements(tournament.id)
  ```

---

## 6. LIVE TOURNAMENT VIEWS (Public-Facing)

**File:** `apps/tournaments/views/live.py` (386 lines)  
**Pattern:** Direct ORM queries for display  
**Service Adoption:** 0 of 3 views use service layer

### 6.1 Live Views

#### TournamentBracketView.get_context_data()
- **Service Calls:** None
- **ORM Usage:** `calls ORM directly`
- **Evidence:**
  ```python
  Tournament.objects.filter(
      is_deleted=False
  ).select_related(
      'game', 'organizer', 'bracket'
  ).prefetch_related(
      Prefetch('matches', ...)
  )
  ```
- **Notes:** Read-only bracket display (acceptable pattern for public views)

#### MatchDetailView.get_context_data()
- **Service Calls:** None
- **ORM Usage:** `calls ORM directly`
- **Evidence:**
  ```python
  Match.objects.filter(
      tournament__slug=tournament_slug,
      is_deleted=False
  ).select_related(...)
  ```
- **Notes:** Read-only match details (acceptable pattern for public views)

#### TournamentResultsView.get_context_data()
- **Service Calls:** None
- **ORM Usage:** `calls ORM directly`
- **Evidence:**
  ```python
  Tournament.objects.filter(
      is_deleted=False
  ).select_related(
      'result', 'result__winner', ...
  )
  ```
- **Notes:** Read-only results display (acceptable pattern for public views)

---

## 7. RESULT SUBMISSION VIEWS (Participant-Facing)

**File:** `apps/tournaments/views/result_submission.py` (200 lines)  
**Pattern:** TODO comments for backend API integration (0% implemented)  
**Service Adoption:** 0 of 2 functions use service layer

### 7.1 Result Submission

#### SubmitResultView.post()
- **Service Calls:** None (TODO comment indicates planned)
- **ORM Usage:** `calls ORM directly` (incomplete implementation)
- **Evidence:**
  ```python
  # TODO: Replace with actual API call
  # POST /api/tournaments/matches/{id}/submit-result/
  ```
- **Status:** Backend integration not yet implemented
- **Business Logic Missing:** Result submission validation, opponent notification, state transitions

#### report_dispute(request, slug, match_id)
- **Service Calls:** None (TODO comment indicates planned)
- **ORM Usage:** `calls ORM directly` (incomplete implementation)
- **Evidence:**
  ```python
  # TODO: Call backend API
  # POST /api/tournaments/matches/{id}/report-dispute/
  ```
- **Status:** Backend integration not yet implemented
- **Business Logic Missing:** Dispute creation, organizer notification, evidence validation

---

## 8. ARCHITECTURAL ANALYSIS

### 8.1 Service Layer Adoption by Module

| Module | Service Calls | Direct ORM | Adoption Rate | Status |
|--------|--------------|------------|---------------|---------|
| **checkin.py** | 8 | 1 (read-only roster) | 89% | ✅ Excellent |
| **lobby.py** | 4 | 0 | 100% | ✅ Excellent |
| **organizer.py** | 1 | 20+ | ~5% | ❌ Poor |
| **organizer_results.py** | 0 | 4 | 0% | ❌ Not Implemented |
| **disputes_management.py** | 0 | 1 | 0% | ❌ Poor |
| **live.py** | 0 | 3 (read-only) | 0% | ⚠️ Acceptable (read-only) |
| **result_submission.py** | 0 | 0 (TODO) | 0% | ❌ Not Implemented |

---

### 8.2 Pattern Comparison

#### ✅ Good Pattern (Participant Views)
```python
# checkin.py - Proper service layer usage
from apps.tournaments.services.check_in_service import CheckInService

def post(self, request, slug):
    registration = CheckInService.check_in(tournament, request.user)
    # Business logic handled in service:
    # - Check-in window validation
    # - Eligibility checks
    # - Timestamp recording
    # - Status updates
    # - Audit logging
```

#### ❌ Anti-Pattern (Organizer Views)
```python
# organizer.py - Direct ORM manipulation
def approve_registration(request, tournament_id, registration_id):
    registration = get_object_or_404(Registration, id=registration_id)
    registration.status = 'confirmed'
    registration.save()
    # Missing business logic:
    # - Email notifications
    # - Audit logging
    # - Status transition validation
    # - Payment verification
```

---

### 8.3 Business Logic Gaps

Functions bypassing service layer lose access to:

1. **Transaction Safety**
   - No atomic operations
   - Risk of partial state updates
   - No rollback on failures

2. **Audit Logging**
   - No action history
   - No user attribution
   - No timestamp tracking

3. **Notifications**
   - No email notifications
   - No in-app notifications
   - No webhook triggers

4. **Validation**
   - No business rule enforcement
   - No state transition validation
   - No permission checks (beyond view-level)

5. **Integration Points**
   - No tournament_ops DTO integration
   - No webhook dispatch
   - No external service calls

---

## 9. RECOMMENDATIONS

### 9.1 Critical Refactoring Needed

**Priority 1: Organizer Registration Actions**
- Refactor `approve_registration()` to call `RegistrationService.approve()`
- Refactor `reject_registration()` to call `RegistrationService.reject()`
- Refactor `bulk_approve_registrations()` to call `RegistrationService.bulk_approve()`
- Refactor `bulk_reject_registrations()` to call `RegistrationService.bulk_reject()`

**Priority 2: Organizer Match Actions**
- Refactor `reschedule_match()` to call `MatchService.reschedule()`
- Refactor `forfeit_match()` to call `MatchService.forfeit()`
- Refactor `override_match_score()` to call `MatchService.override_score()`
- Refactor `cancel_match()` to call `MatchService.cancel()`

**Priority 3: Results Management**
- Implement `MatchService.confirm_result()` and call from `confirm_match_result()`
- Implement `MatchService.reject_result()` and call from `reject_match_result()`
- Implement `MatchService.override_result()` and call from `override_match_result()`

**Priority 4: Dispute Management**
- Implement `DisputeService.create_dispute()` and call from `report_dispute()`
- Implement `DisputeService.get_disputes()` and call from `DisputeManagementView`

---

### 9.2 Service Layer Patterns to Follow

Use **checkin.py** and **lobby.py** as reference implementations:

1. ✅ Import service at top of file
2. ✅ Call service method instead of ORM
3. ✅ Handle ValidationError from service
4. ✅ Let service handle business logic
5. ✅ Return service result to view

**Example Migration:**
```python
# BEFORE (organizer.py)
def approve_registration(request, tournament_id, registration_id):
    registration = get_object_or_404(Registration, id=registration_id)
    registration.status = 'confirmed'
    registration.save()
    return JsonResponse({'success': True})

# AFTER (using service layer)
from apps.tournaments.services.registration_service import RegistrationService

def approve_registration(request, tournament_id, registration_id):
    registration = get_object_or_404(Registration, id=registration_id)
    try:
        approved_registration = RegistrationService.approve(
            registration=registration,
            approved_by=request.user
        )
        return JsonResponse({'success': True})
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
```

---

### 9.3 Read-Only Views Exception

**Acceptable Direct ORM Usage:**
- Public-facing display views (bracket, match detail, results)
- Read-only roster/leaderboard queries
- Export functions (CSV generation)

**Rule:** If view only reads data for display (no state changes), direct ORM is acceptable for performance.

---

## 10. SUMMARY TABLE

### Complete View-to-Service Mapping

| View/Function | File | Service Called | ORM Direct | Status |
|---------------|------|----------------|------------|--------|
| **Organizer Dashboard** |
| `OrganizerDashboardView.get_context_data()` | organizer.py | None | ✅ | Read-only (OK) |
| `OrganizerTournamentDetailView.get_context_data()` | organizer.py | None | ✅ | Read-only (OK) |
| `approve_registration()` | organizer.py | None | ✅ | ❌ Needs refactor |
| `reject_registration()` | organizer.py | None | ✅ | ❌ Needs refactor |
| `bulk_approve_registrations()` | organizer.py | None | ✅ | ❌ Needs refactor |
| `bulk_reject_registrations()` | organizer.py | None | ✅ | ❌ Needs refactor |
| `disqualify_participant()` | organizer.py | `RegistrationService.disqualify_registration()` | ❌ | ✅ Good |
| `verify_payment()` | organizer.py | None | ✅ | ❌ Needs refactor |
| `reject_payment()` | organizer.py | None | ✅ | ❌ Needs refactor |
| `toggle_checkin()` | organizer.py | None | ✅ | ❌ Should use CheckInService |
| `reschedule_match()` | organizer.py | None | ✅ | ❌ Needs refactor |
| `forfeit_match()` | organizer.py | None | ✅ | ❌ Needs refactor |
| `override_match_score()` | organizer.py | None | ✅ | ❌ Needs refactor |
| `cancel_match()` | organizer.py | None | ✅ | ❌ Needs refactor |
| `export_roster_csv()` | organizer.py | None | ✅ | Read-only (OK) |
| `export_payments_csv()` | organizer.py | None | ✅ | Read-only (OK) |
| **Organizer Results** |
| `PendingResultsView.get_queryset()` | organizer_results.py | None | ✅ | Read-only (OK) |
| `confirm_match_result()` | organizer_results.py | None (TODO) | ✅ | ❌ Not implemented |
| `reject_match_result()` | organizer_results.py | None (TODO) | ✅ | ❌ Not implemented |
| `override_match_result()` | organizer_results.py | None (TODO) | ✅ | ❌ Not implemented |
| **Disputes** |
| `DisputeManagementView.get_context_data()` | disputes_management.py | None | ✅ | Read-only (OK) |
| **Check-In (Participant)** |
| `TournamentLobbyView.get_context_data()` | checkin.py | `CheckInService` (4 calls) | ❌ | ✅ Excellent |
| `CheckInActionView.post()` | checkin.py | `CheckInService.check_in()` | ❌ | ✅ Excellent |
| `CheckInActionView._get_error_message()` | checkin.py | `CheckInService` (3 calls) | ❌ | ✅ Excellent |
| `CheckInStatusView.get()` | checkin.py | `CheckInService` (4 calls) | ❌ | ✅ Excellent |
| `RosterView.get()` | checkin.py | None | ✅ | Read-only (OK) |
| **Lobby (Participant)** |
| `TournamentLobbyView.get()` | lobby.py | `LobbyService` (2 calls) | ❌ | ✅ Excellent |
| `CheckInView.post()` | lobby.py | `LobbyService.perform_check_in()` | ❌ | ✅ Excellent |
| `LobbyRosterAPIView.get()` | lobby.py | `LobbyService.get_roster()` | ❌ | ✅ Excellent |
| `LobbyAnnouncementsAPIView.get()` | lobby.py | `LobbyService.get_announcements()` | ❌ | ✅ Excellent |
| **Live (Public)** |
| `TournamentBracketView.get_context_data()` | live.py | None | ✅ | Read-only (OK) |
| `MatchDetailView.get_context_data()` | live.py | None | ✅ | Read-only (OK) |
| `TournamentResultsView.get_context_data()` | live.py | None | ✅ | Read-only (OK) |
| **Result Submission (Participant)** |
| `SubmitResultView.post()` | result_submission.py | None (TODO) | ✅ | ❌ Not implemented |
| `report_dispute()` | result_submission.py | None (TODO) | ✅ | ❌ Not implemented |

---

## 11. CONCLUSION

**Key Takeaway:** Architectural inconsistency detected. Participant-facing views demonstrate proper service layer adoption (89-100%), while organizer console views show poor adoption (~5%). This creates:
1. **Maintenance Burden**: Business logic duplicated across views instead of centralized in services
2. **Testing Gaps**: Direct ORM calls bypass service-level unit tests
3. **Integration Failures**: No tournament_ops DTO integration in organizer actions
4. **Missing Features**: No notifications, audit logging, or validation in organizer workflows

**Recommendation:** Refactor organizer views (organizer.py, organizer_results.py) to match the service layer pattern established in participant views (checkin.py, lobby.py).

---

**End of Audit**
