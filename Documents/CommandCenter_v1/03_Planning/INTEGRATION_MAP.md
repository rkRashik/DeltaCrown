# TRACKER_INTEGRATION_MAP.md

**Initiative:** DeltaCrown Command Center + Lobby Room v1  
**Date:** December 19, 2025  
**Purpose:** Map features to views, services, models, and events

---

## INTEGRATION MAP

| Feature | Existing URL/View | Service Method | Models | Events/Tasks | Notes |
|---------|-------------------|----------------|---------|--------------|-------|
| **Organizer - Registration Management** |
| Approve registration | `/tournaments/<slug>/organizer/registrations/<id>/approve/`<br>`organizer.py::approve_registration()` | **MISSING**<br>`RegistrationService.approve()` | Registration | Email: confirmation<br>Audit: registration_approved<br>Webhook: registration.approved | Currently calls `.save()` directly (ADR-002 violation) |
| Reject registration | `/tournaments/<slug>/organizer/registrations/<id>/reject/`<br>`organizer.py::reject_registration()` | **MISSING**<br>`RegistrationService.reject()` | Registration | Email: rejection notice<br>Audit: registration_rejected<br>Webhook: registration.rejected | Currently calls `.save()` directly |
| Bulk approve registrations | `/tournaments/<slug>/organizer/registrations/bulk-approve/`<br>`organizer.py::bulk_approve_registrations()` | **MISSING**<br>`RegistrationService.bulk_approve()` | Registration | Email: bulk confirmation<br>Audit: bulk entries<br>Webhook: batch event | Currently uses `.update()` without side effects |
| Bulk reject registrations | `/tournaments/<slug>/organizer/registrations/bulk-reject/`<br>`organizer.py::bulk_reject_registrations()` | **MISSING**<br>`RegistrationService.bulk_reject()` | Registration | Email: bulk rejection<br>Audit: bulk entries<br>Webhook: batch event | Currently loops with `.save()` without side effects |
| **Organizer - Payment Management** |
| Verify payment | `/tournaments/<slug>/organizer/payments/<id>/verify/`<br>`organizer.py::verify_payment()` | **MISSING**<br>`PaymentService.verify()` | Payment, Registration | Email: payment confirmed<br>Audit: payment_verified<br>Update registration status | Currently calls `.save()` directly |
| Reject payment | `/tournaments/<slug>/organizer/payments/<id>/reject/`<br>`organizer.py::reject_payment()` | **MISSING**<br>`PaymentService.reject()` | Payment, Registration | Email: payment rejected<br>Audit: payment_rejected<br>Refund processing | Currently calls `.save()` directly |
| **Organizer - Check-In Management** |
| Toggle check-in (organizer override) | `/tournaments/<slug>/organizer/registrations/<id>/toggle-checkin/`<br>`organizer.py::toggle_checkin()` | **MISSING**<br>`CheckInService.toggle()` | Registration, CheckIn | Audit: checkin_toggled<br>WebSocket: roster.updated (Phase 2) | Currently manipulates `checked_in` field directly. Should use CheckInService which exists but lacks toggle method. |
| **Participant - Check-In** |
| Participant check-in | `/tournaments/<slug>/check-in/`<br>`checkin.py::CheckInActionView.post()` | **EXISTS** ✅<br>`CheckInService.check_in()` | Registration, CheckIn | Audit: checkin_performed<br>WebSocket: roster.updated (Phase 2) | Gold standard implementation - properly uses service layer |
| **Participant - Match Results** |
| Submit match result | `/tournaments/<slug>/matches/<id>/submit-result/`<br>`result_submission.py::SubmitResultView.post()` | **MISSING**<br>`MatchService.submit_result()` | Match | Email: opponent notification<br>Audit: result_submitted<br>WebSocket: match.updated (Phase 2) | Currently has TODO comment "Call backend API". Incomplete implementation. |
| **Organizer - Match Results Management** |
| Confirm match result | `/tournaments/<slug>/organizer/results/<id>/confirm/`<br>`organizer_results.py::confirm_match_result()` | **MISSING**<br>`MatchService.confirm_result()` | Match, Bracket | Email: participants notified<br>Audit: result_confirmed<br>Bracket progression<br>tournament_ops integration | Currently has TODO comment "Call backend API". Incomplete implementation. |
| Reject match result | `/tournaments/<slug>/organizer/results/<id>/reject/`<br>`organizer_results.py::reject_match_result()` | **MISSING**<br>`MatchService.reject_result()` | Match | Email: participants notified<br>Audit: result_rejected<br>Reset match state | Currently has TODO comment "Implement rejection logic". Incomplete implementation. |
| Override match result | `/tournaments/<slug>/organizer/results/<id>/override/`<br>`organizer_results.py::override_match_result()` | **MISSING**<br>`MatchService.override_result()` | Match, Bracket | Email: participants notified<br>Audit: result_overridden<br>Bracket progression<br>tournament_ops integration | Currently has TODO comment "Call backend API or use MatchService". Incomplete implementation. |
| **Participant - Dispute Management** |
| Report match dispute | `/tournaments/<slug>/matches/<id>/report-dispute/`<br>`result_submission.py::report_dispute()` | **MISSING**<br>`DisputeService.create_dispute()` | Dispute, Match | Email: organizer notification<br>Audit: dispute_created<br>WebSocket: dispute.created (Phase 2)<br>Update match state to DISPUTED | Currently has TODO comment "Call backend API". Incomplete implementation. |
| **Organizer - Dispute Management** |
| View disputes | `/tournaments/<slug>/organizer/disputes/`<br>`disputes_management.py::DisputeManagementView` | N/A (read-only) | Dispute, Match | None (display only) | Currently uses direct ORM query (acceptable for read-only view) |
| Resolve dispute | `/tournaments/<slug>/organizer/disputes/<id>/resolve/`<br>**NOT IMPLEMENTED YET** | **MISSING**<br>`DisputeService.resolve_dispute()` | Dispute, Match | Email: participants notified<br>Audit: dispute_resolved<br>Apply resolution (score change if needed)<br>WebSocket: dispute.resolved (Phase 2) | View endpoint does not exist yet. Must create in Phase 0/1. |
| **Organizer - Match Management** |
| Reschedule match | `/tournaments/<slug>/organizer/matches/<id>/reschedule/`<br>`organizer.py::reschedule_match()` | **MISSING**<br>`MatchService.reschedule()` | Match | Email: participants notified<br>Audit: match_rescheduled<br>Conflict detection<br>WebSocket: match.updated (Phase 2) | Currently updates `scheduled_time` directly without validation or notifications |
| Forfeit match | `/tournaments/<slug>/organizer/matches/<id>/forfeit/`<br>`organizer.py::forfeit_match()` | **MISSING**<br>`MatchService.forfeit()` | Match, Bracket | Email: participants notified<br>Audit: match_forfeited<br>Bracket progression<br>tournament_ops integration | Currently sets `state=FORFEIT` and `winner_id` directly without bracket progression |
| Cancel match | `/tournaments/<slug>/organizer/matches/<id>/cancel/`<br>`organizer.py::cancel_match()` | **MISSING**<br>`MatchService.cancel()` | Match | Email: participants notified<br>Audit: match_cancelled<br>WebSocket: match.updated (Phase 2) | Currently sets `state=CANCELLED` directly |
| Override match score | `/tournaments/<slug>/organizer/matches/<id>/override-score/`<br>`organizer.py::override_match_score()` | **MISSING**<br>`MatchService.override_score()` | Match, Bracket | Email: participants notified<br>Audit: score_overridden<br>Bracket progression<br>tournament_ops integration | Currently updates scores and winner directly without bracket progression |
| **Tournament Operations** |
| Generate bracket | `/tournaments/<slug>/organizer/bracket/generate/`<br>**VIEW EXISTS** | **EXISTS** ✅<br>`BracketService.generate_bracket()`<br>→ `BracketEngineService` (tournament_ops) | Tournament, Bracket, Registration | Audit: bracket_generated<br>Notification: bracket ready<br>tournament_ops: BracketGenerationDTO | Service exists and integrates with tournament_ops. One of few services used correctly. |
| Stage transition | `/tournaments/<slug>/organizer/transition/`<br>**VIEW EXISTS** | **EXISTS** ✅<br>`StageTransitionService.transition()`<br>→ `StageTransitionEngineService` (tournament_ops) | Tournament | Audit: stage_transitioned<br>tournament_ops: StageTransitionDTO | Service exists and integrates with tournament_ops. Workflow marked READY. |
| **Lobby Room (Participant)** |
| View lobby roster | `/tournaments/<slug>/lobby/`<br>`lobby.py::TournamentLobbyView.get()` | **EXISTS** ✅<br>`LobbyService.get_roster()` | Registration, CheckIn, Team | WebSocket: roster.updated (Phase 2) | Gold standard implementation - properly uses service for data aggregation |
| Get roster (API) | `/tournaments/<slug>/lobby/roster/`<br>`lobby.py::LobbyRosterAPIView.get()` | **EXISTS** ✅<br>`LobbyService.get_roster()` | Registration, CheckIn, Team | None (read-only API) | Returns JSON for HTMX updates |
| Get announcements | `/tournaments/<slug>/lobby/`<br>`lobby.py::TournamentLobbyView.get()` | **EXISTS** ✅<br>`LobbyService.get_announcements()` | Announcement | WebSocket: announcement.new (Phase 2) | Gold standard implementation - properly uses service |
| Get announcements (API) | `/tournaments/<slug>/lobby/announcements/`<br>`lobby.py::LobbyAnnouncementsAPIView.get()` | **EXISTS** ✅<br>`LobbyService.get_announcements()` | Announcement | None (read-only API) | Returns JSON for HTMX updates |
| Participant check-in (lobby) | `/tournaments/<slug>/lobby/check-in/`<br>`lobby.py::CheckInView.post()` | **EXISTS** ✅<br>`LobbyService.perform_check_in()` | CheckIn, Registration, Team | WebSocket: roster.updated (Phase 2) | Alternative to checkin.py implementation. Both use service correctly. |
| **Lobby Room (Organizer)** |
| Post announcement | `/tournaments/<slug>/organizer/announcements/post/`<br>**NOT IMPLEMENTED YET** | **MISSING**<br>`LobbyService.post_announcement()` | Announcement | WebSocket: announcement.new (Phase 2) | View endpoint does not exist yet. Service method needed for Phase 2. |

---

## SUMMARY STATISTICS

### Service Layer Adoption

| Category | Total Features | Uses Services | Missing Services | Adoption Rate |
|----------|----------------|---------------|------------------|---------------|
| **Organizer Actions** | 15 | 2 (13%) | 13 (87%) | ❌ 13% |
| **Participant Actions** | 5 | 3 (60%) | 2 (40%) | ⚠️ 60% |
| **Lobby/Check-In** | 5 | 5 (100%) | 0 (0%) | ✅ 100% |
| **Tournament Ops** | 2 | 2 (100%) | 0 (0%) | ✅ 100% |
| **TOTAL** | 27 | 12 (44%) | 15 (56%) | ⚠️ 44% |

### Current State Analysis

**Gold Standard Implementations (Use Services Correctly):**
1. ✅ Participant check-in (`checkin.py` - uses `CheckInService`)
2. ✅ Lobby roster (`lobby.py` - uses `LobbyService.get_roster()`)
3. ✅ Lobby announcements (`lobby.py` - uses `LobbyService.get_announcements()`)
4. ✅ Bracket generation (uses `BracketService` → `tournament_ops`)
5. ✅ Stage transition (uses `StageTransitionService` → `tournament_ops`)

**Anti-Pattern Implementations (Bypass Services):**
1. ❌ 11 organizer actions in `organizer.py` (direct ORM writes)
2. ❌ 3 result management actions in `organizer_results.py` (TODO comments)
3. ❌ 2 participant actions in `result_submission.py` (TODO comments)

**Not Implemented:**
1. ❌ Dispute resolution view/service
2. ❌ Post announcement view/service

---

## PHASE 0 PRIORITY (Missing Service Methods)

**Critical Path for Service Layer Refactor:**

1. `RegistrationService.approve()` - Backlog #1
2. `RegistrationService.reject()` - Backlog #2
3. `RegistrationService.bulk_approve()` - Backlog #3
4. `RegistrationService.bulk_reject()` - Backlog #4
5. `PaymentService.verify()` - Backlog #5
6. `PaymentService.reject()` - Backlog #6
7. `CheckInService.toggle()` - Backlog #7
8. `MatchService.reschedule()` - Backlog #8
9. `MatchService.forfeit()` - Backlog #9
10. `MatchService.cancel()` - Backlog #10
11. `MatchService.override_score()` - Backlog #11
12. `MatchService.confirm_result()` - Backlog #12
13. `MatchService.reject_result()` - Backlog #13
14. `MatchService.override_result()` - Backlog #14
15. `MatchService.submit_result()` - Backlog #15
16. `DisputeService.create_dispute()` - Backlog #16
17. `DisputeService.resolve_dispute()` - Backlog #17

---

## PHASE 2 WEBSOCKET EVENTS (Real-Time Updates)

| Event Name | Triggered By | Consumers | Payload |
|------------|--------------|-----------|---------|
| `roster.updated` | `CheckInService.check_in()`<br>`RegistrationService.approve()` | Lobby participants | Updated roster data (LobbyService.get_roster()) |
| `announcement.new` | `LobbyService.post_announcement()` | Lobby participants | Announcement object (id, title, message, type, posted_by, created_at) |
| `match.updated` | `MatchService.reschedule()`<br>`MatchService.forfeit()`<br>`MatchService.confirm_result()` | Match participants<br>Lobby participants | Match object (id, state, scheduled_time, scores, winner) |
| `dispute.created` | `DisputeService.create_dispute()` | Tournament organizers | Dispute object (id, match_id, reported_by, reason, created_at) |
| `dispute.resolved` | `DisputeService.resolve_dispute()` | Match participants | Dispute object (id, resolution, resolved_by, resolved_at) |

---

## INTEGRATION DEPENDENCIES

### tournament_ops Integration Points

**Existing (via Services):**
- `BracketService.generate_bracket()` → `BracketEngineService.generate(BracketGenerationDTO)`
- `StageTransitionService.transition()` → `StageTransitionEngineService.execute(StageTransitionDTO)`

**Missing (Planned):**
- `MatchService.confirm_result()` → Should trigger bracket progression via tournament_ops
- `MatchService.override_result()` → Should trigger bracket progression via tournament_ops
- `MatchService.forfeit()` → Should trigger bracket progression via tournament_ops

**Critical:** Organizer views currently bypass services, so tournament_ops integration points are unreachable.

---

## NOTES

1. **Gold Standard Pattern:** `checkin.py` and `lobby.py` demonstrate correct service usage. All refactored views should follow this pattern.

2. **Anti-Pattern:** `organizer.py` contains 11 functions with direct ORM writes (`.save()`, `.update()`). All must be refactored in Phase 0.

3. **Incomplete Implementations:** `organizer_results.py` and `result_submission.py` have TODO comments indicating planned service integration not yet implemented.

4. **Read-Only Views:** `DisputeManagementView` uses direct ORM query (acceptable for read-only display). Write operations (resolve dispute) need service.

5. **Missing Endpoints:** Dispute resolution and announcement posting have no view endpoints yet. Must be created in Phase 1/2.

6. **WebSocket Events:** Phase 2 will add real-time updates. Services must dispatch WebSocket events after state changes.

7. **Cache Invalidation:** Services should invalidate Redis cache keys after state changes (Phase 3 optimization).

---

**Last Updated:** December 19, 2025  
**Source:** Based on 01_ARCHITECTURE_CURRENT_STATE.md and 04_VIEW_TO_SERVICE_CALLMAP.md audits
