# 04_BACKLOG.md

**Initiative:** DeltaCrown Command Center + Lobby Room v1  
**Date:** December 19, 2025  
**Status:** Backlog - Prioritized

---

## PHASE 0: SERVICE LAYER REFACTOR (Priority 1-25)

### Backend - Services

#### 1. Create RegistrationService.approve()
- **Phase:** 0
- **Area:** Services
- **Definition of Done:**
  - Method accepts `registration` and `approved_by` parameters
  - Validates registration status, updates to CONFIRMED, sets approved_by/approved_at
  - Sends confirmation email, creates audit log, dispatches webhook
  - Raises ValidationError for invalid operations
  - Unit tests with 100% coverage
- **References:** `apps/tournaments/services/registration_service.py`

#### 2. Create RegistrationService.reject()
- **Phase:** 0
- **Area:** Services
- **Definition of Done:**
  - Method accepts `registration`, `rejected_by`, and `reason` parameters
  - Validates registration status, updates to REJECTED, records reason
  - Sends rejection email, creates audit log
  - Unit tests with 100% coverage
- **References:** `apps/tournaments/services/registration_service.py`

#### 3. Create RegistrationService.bulk_approve()
- **Phase:** 0
- **Area:** Services
- **Definition of Done:**
  - Method accepts list of `registration_ids` and `approved_by`
  - Wraps in @transaction.atomic, validates all, approves all or none
  - Sends bulk emails, creates audit logs for each
  - Unit tests including rollback scenarios
- **References:** `apps/tournaments/services/registration_service.py`

#### 4. Create RegistrationService.bulk_reject()
- **Phase:** 0
- **Area:** Services
- **Definition of Done:**
  - Method accepts list of `registration_ids`, `rejected_by`, and `reason`
  - Wraps in @transaction.atomic, validates all, rejects all or none
  - Sends bulk emails, creates audit logs
  - Unit tests including rollback scenarios
- **References:** `apps/tournaments/services/registration_service.py`

#### 5. Create PaymentService.verify()
- **Phase:** 0
- **Area:** Services
- **Definition of Done:**
  - Method accepts `payment` and `verified_by` parameters
  - Updates payment status to VERIFIED, records timestamp
  - Updates related registration status if applicable
  - Sends confirmation email, creates audit log
  - Unit tests with 100% coverage
- **References:** `apps/tournaments/services/payment_service.py`

#### 6. Create PaymentService.reject()
- **Phase:** 0
- **Area:** Services
- **Definition of Done:**
  - Method accepts `payment`, `rejected_by`, and `reason` parameters
  - Updates payment status to REJECTED, records reason
  - Sends rejection email, creates audit log
  - Unit tests with 100% coverage
- **References:** `apps/tournaments/services/payment_service.py`

#### 7. Create CheckInService.toggle()
- **Phase:** 0
- **Area:** Services
- **Definition of Done:**
  - Method accepts `registration` and `toggled_by` parameters (organizer override)
  - Validates check-in window if checking in, toggles checked_in status
  - Records timestamp, creates audit log
  - Unit tests with 100% coverage
- **References:** `apps/tournaments/services/check_in_service.py`

#### 8. Create MatchService.reschedule()
- **Phase:** 0
- **Area:** Services
- **Definition of Done:**
  - Method accepts `match`, `new_scheduled_time`, and `rescheduled_by`
  - Validates match state, checks for conflicts, updates scheduled_time
  - Sends notification to participants, creates audit log
  - Unit tests with 100% coverage
- **References:** `apps/tournaments/services/match_service.py`

#### 9. Create MatchService.forfeit()
- **Phase:** 0
- **Area:** Services
- **Definition of Done:**
  - Method accepts `match`, `forfeiting_participant_id`, and `forfeited_by`
  - Updates match state to FORFEIT, sets winner_id to opponent
  - Triggers bracket progression, sends notifications, creates audit log
  - Unit tests with 100% coverage
- **References:** `apps/tournaments/services/match_service.py`

#### 10. Create MatchService.cancel()
- **Phase:** 0
- **Area:** Services
- **Definition of Done:**
  - Method accepts `match` and `cancelled_by` parameters
  - Updates match state to CANCELLED
  - Sends notifications to participants, creates audit log
  - Unit tests with 100% coverage
- **References:** `apps/tournaments/services/match_service.py`

#### 11. Create MatchService.override_score()
- **Phase:** 0
- **Area:** Services
- **Definition of Done:**
  - Method accepts `match`, `participant1_score`, `participant2_score`, `overridden_by`
  - Validates scores, updates match scores and winner_id, sets state to COMPLETED
  - Triggers bracket progression, sends notifications, creates audit log
  - Unit tests with 100% coverage
- **References:** `apps/tournaments/services/match_service.py`

#### 12. Create MatchService.confirm_result()
- **Phase:** 0
- **Area:** Services
- **Definition of Done:**
  - Method accepts `match` and `confirmed_by` (organizer)
  - Updates match state to COMPLETED, confirms submitted scores
  - Triggers bracket progression, sends notifications, creates audit log
  - Unit tests with 100% coverage
- **References:** `apps/tournaments/services/match_service.py`

#### 13. Create MatchService.reject_result()
- **Phase:** 0
- **Area:** Services
- **Definition of Done:**
  - Method accepts `match`, `rejected_by`, and `reason`
  - Resets match state to LIVE or PENDING_RESULT, clears submitted scores
  - Sends notifications to participants, creates audit log
  - Unit tests with 100% coverage
- **References:** `apps/tournaments/services/match_service.py`

#### 14. Create MatchService.override_result()
- **Phase:** 0
- **Area:** Services
- **Definition of Done:**
  - Method accepts `match`, new scores, `overridden_by`, and `reason`
  - Overrides participant-submitted scores with organizer values
  - Updates state to COMPLETED, triggers bracket progression
  - Unit tests with 100% coverage
- **References:** `apps/tournaments/services/match_service.py`

#### 15. Create MatchService.submit_result()
- **Phase:** 0
- **Area:** Services
- **Definition of Done:**
  - Method accepts `match`, `submitted_by`, scores, and `evidence_url`
  - Validates participant is in match, updates submitted scores
  - Sets state to PENDING_RESULT, sends notification to opponent
  - Unit tests with 100% coverage
- **References:** `apps/tournaments/services/match_service.py`

#### 16. Create DisputeService.create_dispute()
- **Phase:** 0
- **Area:** Services
- **Definition of Done:**
  - Method accepts `match`, `reported_by`, `reason`, `description`, and `evidence_url`
  - Creates Dispute record, updates match state to DISPUTED
  - Sends notification to organizers, creates audit log
  - Unit tests with 100% coverage
- **References:** `apps/tournaments/services/dispute_service.py`

#### 17. Create DisputeService.resolve_dispute()
- **Phase:** 0
- **Area:** Services
- **Definition of Done:**
  - Method accepts `dispute`, `resolved_by`, `resolution`, and `resolution_notes`
  - Updates dispute status to RESOLVED, applies resolution (match score change if needed)
  - Sends notifications to participants, creates audit log
  - Unit tests with 100% coverage
- **References:** `apps/tournaments/services/dispute_service.py`

#### 18. Enhance NotificationService (email dispatch)
- **Phase:** 0
- **Area:** Services
- **Definition of Done:**
  - Methods for all notification types (registration approved/rejected, payment verified/rejected, match rescheduled, result confirmed, dispute created/resolved)
  - Email templates for each notification type
  - Unit tests mocking email send
- **References:** `apps/tournaments/services/notification_service.py`

#### 19. Create AuditService (audit logging)
- **Phase:** 0
- **Area:** Services
- **Definition of Done:**
  - Method `log_action(action, user, tournament, target_id, metadata)` creates AuditLog record
  - Captures who, what, when, why for all state changes
  - Unit tests verify log creation
- **References:** `apps/tournaments/services/audit_service.py`

### Backend - View Refactoring

#### 20. Refactor organizer.py registration actions
- **Phase:** 0
- **Area:** Organizer
- **Definition of Done:**
  - `approve_registration()`, `reject_registration()`, `bulk_approve_registrations()`, `bulk_reject_registrations()` delegate to RegistrationService
  - No `.save()` or `.update()` calls in view functions
  - Integration tests pass, regression tests pass
- **References:** `apps/tournaments/views/organizer.py` (lines 1-500)

#### 21. Refactor organizer.py payment actions
- **Phase:** 0
- **Area:** Organizer
- **Definition of Done:**
  - `verify_payment()`, `reject_payment()` delegate to PaymentService
  - No `.save()` calls in view functions
  - Integration tests pass
- **References:** `apps/tournaments/views/organizer.py` (lines 500-800)

#### 22. Refactor organizer.py check-in and match actions
- **Phase:** 0
- **Area:** Organizer
- **Definition of Done:**
  - `toggle_checkin()` delegates to CheckInService
  - `reschedule_match()`, `forfeit_match()`, `cancel_match()`, `override_match_score()` delegate to MatchService
  - No `.save()` calls in view functions
  - Integration tests pass
- **References:** `apps/tournaments/views/organizer.py` (lines 800-1484)

#### 23. Refactor organizer_results.py result actions
- **Phase:** 0
- **Area:** Organizer
- **Definition of Done:**
  - `confirm_match_result()`, `reject_match_result()`, `override_match_result()` delegate to MatchService
  - All TODO comments removed
  - Integration tests pass
- **References:** `apps/tournaments/views/organizer_results.py`

#### 24. Refactor result_submission.py participant actions
- **Phase:** 0
- **Area:** Lobby
- **Definition of Done:**
  - `submit_result()` delegates to MatchService.submit_result()
  - `report_dispute()` delegates to DisputeService.create_dispute()
  - All TODO comments removed
  - Integration tests pass
- **References:** `apps/tournaments/views/result_submission.py`

### QA - Phase 0

#### 25. Phase 0 regression testing and deployment
- **Phase:** 0
- **Area:** QA
- **Definition of Done:**
  - All existing integration tests pass
  - Manual testing of refactored workflows (registration approval, payment verification, match actions)
  - Staging deployment validated
  - Organizer beta testing (5-10 users) completed with sign-off
  - Production deployment completed with monitoring

---

## PHASE 1: COMMAND CENTER MVP (Priority 26-45)

### Frontend - Templates

#### 26. Create Command Center dashboard template
- **Phase:** 1
- **Area:** Organizer
- **Definition of Done:**
  - `templates/tournaments/organizer/command_center.html` created with Tailwind layout
  - Stats cards section (registrations, checked in, pending results, open disputes)
  - Widget containers for registrations, results, disputes
  - Responsive design (desktop, tablet, mobile)
- **References:** New file

#### 27. Create registration management widget
- **Phase:** 1
- **Area:** Organizer
- **Definition of Done:**
  - `templates/tournaments/organizer/_registrations_widget.html` created
  - List of pending registrations with approve/reject buttons
  - Bulk action checkboxes and bulk approve/reject buttons
  - HTMX attributes for auto-refresh (every 10s)
- **References:** New file

#### 28. Create results management widget
- **Phase:** 1
- **Area:** Organizer
- **Definition of Done:**
  - `templates/tournaments/organizer/_results_widget.html` created
  - List of pending results with confirm/reject/override buttons
  - HTMX attributes for auto-refresh (every 10s)
- **References:** New file

#### 29. Create disputes management widget
- **Phase:** 1
- **Area:** Organizer
- **Definition of Done:**
  - `templates/tournaments/organizer/_disputes_widget.html` created
  - List of open disputes with view details and resolve buttons
  - HTMX attributes for auto-refresh (every 10s)
- **References:** New file

#### 30. Create Tailwind component library
- **Phase:** 1
- **Area:** Organizer
- **Definition of Done:**
  - `static/css/components/command_center.css` created with reusable components
  - Button styles (btn-primary, btn-secondary, btn-danger)
  - Card styles (card, stat-card, list-card)
  - Table styles (responsive, sortable)
  - Modal styles (confirmation dialogs)
- **References:** New file

### Frontend - JavaScript

#### 31. Create registration actions module
- **Phase:** 1
- **Area:** Organizer
- **Definition of Done:**
  - `static/js/command_center/registration_actions.js` created
  - Event listeners for approve, reject, bulk approve, bulk reject buttons
  - AJAX calls to backend endpoints with CSRF token
  - Toast notifications on success/error
- **References:** New file

#### 32. Create result actions module
- **Phase:** 1
- **Area:** Organizer
- **Definition of Done:**
  - `static/js/command_center/result_actions.js` created
  - Event listeners for confirm, reject, override buttons
  - AJAX calls to backend endpoints
  - Confirmation modals for destructive actions (reject, override)
- **References:** New file

#### 33. Create dispute actions module
- **Phase:** 1
- **Area:** Organizer
- **Definition of Done:**
  - `static/js/command_center/dispute_actions.js` created
  - Event listeners for resolve button
  - Modal for resolution form (resolution decision, notes)
  - AJAX call to backend endpoint
- **References:** New file

#### 34. Create notifications module
- **Phase:** 1
- **Area:** Organizer
- **Definition of Done:**
  - `static/js/command_center/notifications.js` created
  - `showToast(message, type)` function for success/error notifications
  - Auto-dismiss after 3 seconds
  - Styled with Tailwind classes
- **References:** New file

#### 35. Create modals module
- **Phase:** 1
- **Area:** Organizer
- **Definition of Done:**
  - `static/js/command_center/modals.js` created
  - `showConfirmationModal(title, message, onConfirm)` function
  - Styled confirmation dialogs with cancel/confirm buttons
  - Escape key and backdrop click to close
- **References:** New file

### Backend - Views

#### 36. Refactor OrganizerDashboardView
- **Phase:** 1
- **Area:** Organizer
- **Definition of Done:**
  - View renders new `command_center.html` template
  - Context includes stats (total registrations, checked in, pending results, open disputes)
  - URL remains `/tournaments/<slug>/organizer/` (backward compatible)
- **References:** `apps/tournaments/views/organizer.py`

#### 37. Create HTMX partial endpoints
- **Phase:** 1
- **Area:** Organizer
- **Definition of Done:**
  - `registrations_widget_partial()` view returns `_registrations_widget.html`
  - `results_widget_partial()` view returns `_results_widget.html`
  - `disputes_widget_partial()` view returns `_disputes_widget.html`
  - Views use services for data aggregation
- **References:** `apps/tournaments/views/organizer.py`

### QA - Phase 1

#### 38. Cross-browser testing
- **Phase:** 1
- **Area:** QA
- **Definition of Done:**
  - Command Center tested on Chrome, Firefox, Safari, Edge
  - All actions work (approve, reject, confirm, resolve)
  - Responsive design validated on desktop (1920px), tablet (768px), mobile (375px)
  - No visual regressions

#### 39. Accessibility testing
- **Phase:** 1
- **Area:** QA
- **Definition of Done:**
  - WCAG 2.1 AA compliance verified with axe DevTools
  - Keyboard navigation works for all actions
  - Screen reader testing completed (NVDA/VoiceOver)
  - Color contrast ratios validated

#### 40. Performance testing
- **Phase:** 1
- **Area:** QA
- **Definition of Done:**
  - Lighthouse score 90+ for performance, accessibility, best practices
  - Page load time <2s on staging
  - AJAX response time <200ms measured

#### 41. User acceptance testing
- **Phase:** 1
- **Area:** QA
- **Definition of Done:**
  - 10-15 organizers complete UAT scenarios
  - Task completion rate 95%+
  - Satisfaction survey 90%+ positive
  - Critical bugs resolved, minor bugs triaged

#### 42. Phase 1 staging deployment
- **Phase:** 1
- **Area:** QA
- **Definition of Done:**
  - Command Center deployed to staging
  - Smoke tests pass
  - Monitoring configured (error tracking, performance)

#### 43. Phase 1 production deployment
- **Phase:** 1
- **Area:** Organizer
- **Definition of Done:**
  - Opt-in beta rollout (feature flag for new UI)
  - 10% → 50% → 100% gradual rollout over 1 week
  - Monitoring active (error rates, task completion time)
  - Rollback plan ready and tested

---

## PHASE 2: LOBBY ROOM vNEXT (Priority 44-60)

### Infra - Real-Time Infrastructure

#### 44. Setup Django Channels + Redis
- **Phase:** 2
- **Area:** Infra
- **Definition of Done:**
  - Django Channels installed and configured
  - Redis configured as channel layer (staging and production)
  - WebSocket routing configured
  - Connection test endpoint working

#### 45. Create lobby WebSocket consumer
- **Phase:** 2
- **Area:** Lobby
- **Definition of Done:**
  - `consumers/lobby_consumer.py` created
  - Handles connect, disconnect, roster_update, announcement_new, match_updated events
  - Joins room group `lobby_{tournament_slug}`
  - Unit tests for consumer logic
- **References:** New file

#### 46. Integrate WebSocket dispatch in services
- **Phase:** 2
- **Area:** Services
- **Definition of Done:**
  - CheckInService.check_in() dispatches `roster.updated` event
  - RegistrationService.approve() dispatches `roster.updated` event
  - LobbyService.post_announcement() dispatches `announcement.new` event
  - MatchService methods dispatch `match.updated` event
  - Unit tests verify event dispatch
- **References:** `apps/tournaments/services/check_in_service.py`, `lobby_service.py`, `match_service.py`

### Frontend - Templates

#### 47. Create enhanced lobby hub template
- **Phase:** 2
- **Area:** Lobby
- **Definition of Done:**
  - `templates/tournaments/lobby/hub_v2.html` created with Tailwind layout
  - Roster section with real-time updates
  - Announcements section
  - Next match widget
  - Match schedule section
- **References:** New file

#### 48. Create announcements widget
- **Phase:** 2
- **Area:** Lobby
- **Definition of Done:**
  - `templates/tournaments/lobby/_announcements.html` created
  - Displays pinned and recent announcements
  - Auto-updates when new announcements posted
- **References:** New file

#### 49. Create next match widget
- **Phase:** 2
- **Area:** Lobby
- **Definition of Done:**
  - `templates/tournaments/lobby/_next_match.html` created
  - Displays participant's next scheduled match
  - Countdown timer until match start
  - Lobby info (if available)
- **References:** New file

#### 50. Create complete result submission form
- **Phase:** 2
- **Area:** Lobby
- **Definition of Done:**
  - `templates/tournaments/matches/submit_result.html` created
  - Form with participant1_score, participant2_score, evidence_url, notes fields
  - Client-side validation (scores required, non-negative, not tied)
  - Submit button triggers JavaScript
- **References:** `apps/tournaments/views/result_submission.py` (refactor template)

#### 51. Create complete dispute submission form
- **Phase:** 2
- **Area:** Lobby
- **Definition of Done:**
  - `templates/tournaments/matches/dispute_form.html` created
  - Form with reason dropdown, description textarea, evidence_url field
  - Client-side validation (reason and description required)
  - Submit button triggers JavaScript
- **References:** New file

### Frontend - JavaScript

#### 52. Create WebSocket client module
- **Phase:** 2
- **Area:** Lobby
- **Definition of Done:**
  - `static/js/lobby/websocket_client.js` created
  - Establishes WebSocket connection on page load
  - Handles reconnection on disconnect
  - Dispatches events to listeners
  - Graceful fallback to polling if WebSocket unavailable
- **References:** New file

#### 53. Create roster updates module
- **Phase:** 2
- **Area:** Lobby
- **Definition of Done:**
  - `static/js/lobby/roster_updates.js` created
  - Listens for `roster.updated` WebSocket events
  - Updates roster DOM without page reload
  - Highlights newly checked-in participants
- **References:** New file

#### 54. Create announcements module
- **Phase:** 2
- **Area:** Lobby
- **Definition of Done:**
  - `static/js/lobby/announcements.js` created
  - Listens for `announcement.new` WebSocket events
  - Prepends new announcements to list
  - Shows toast notification for new announcements
- **References:** New file

#### 55. Create result submission module
- **Phase:** 2
- **Area:** Lobby
- **Definition of Done:**
  - `static/js/matches/result_submission.js` created
  - Handles form submission via AJAX
  - Validates scores (non-negative, not tied)
  - Shows success/error toast
  - Redirects to match detail on success
- **References:** New file

#### 56. Create dispute submission module
- **Phase:** 2
- **Area:** Lobby
- **Definition of Done:**
  - `static/js/matches/dispute_submission.js` created
  - Handles form submission via AJAX
  - Validates reason and description required
  - Shows success/error toast
  - Redirects to match detail on success
- **References:** New file

### Backend - Services

#### 57. Create LobbyService.post_announcement()
- **Phase:** 2
- **Area:** Services
- **Definition of Done:**
  - Method accepts `tournament`, `posted_by`, `title`, `message`, `announcement_type`, `is_pinned`
  - Creates Announcement record
  - Dispatches `announcement.new` WebSocket event
  - Unit tests verify announcement creation and event dispatch
- **References:** `apps/tournaments/services/lobby_service.py`

#### 58. Create LobbyService.get_next_match()
- **Phase:** 2
- **Area:** Services
- **Definition of Done:**
  - Method accepts `tournament` and `user`
  - Returns next scheduled match for participant
  - Includes countdown seconds until match start
  - Unit tests with various match states
- **References:** `apps/tournaments/services/lobby_service.py`

### QA - Phase 2

#### 59. WebSocket load testing
- **Phase:** 2
- **Area:** QA
- **Definition of Done:**
  - 100 concurrent WebSocket connections maintained for 10 minutes
  - Latency <1s for events
  - Connection stability 99%+
  - No memory leaks detected

#### 60. Phase 2 UAT and production deployment
- **Phase:** 2
- **Area:** QA
- **Definition of Done:**
  - 50-100 participants complete UAT scenarios
  - Result submission completion rate 90%+
  - Participant satisfaction 85%+
  - Gradual rollout (10% → 50% → 100%) completed
  - All TODO comments removed from result_submission.py and disputes_management.py

---

## PHASE 3: AUTOMATION & POLISH (Priority 61-75)

### QA - Automated Testing

#### 61. Create Cypress E2E tests for organizer workflows
- **Phase:** 3
- **Area:** QA
- **Definition of Done:**
  - E2E tests for: approve registration, reject registration, verify payment, confirm result, resolve dispute
  - Tests run in CI/CD pipeline
  - 90%+ workflow coverage
- **References:** New `tests/e2e/organizer_*.spec.js` files

#### 62. Create Cypress E2E tests for participant workflows
- **Phase:** 3
- **Area:** QA
- **Definition of Done:**
  - E2E tests for: check-in, view roster, submit result, report dispute
  - Tests run in CI/CD pipeline
  - 90%+ workflow coverage
- **References:** New `tests/e2e/participant_*.spec.js` files

#### 63. Create Locust load tests
- **Phase:** 3
- **Area:** QA
- **Definition of Done:**
  - Load test for Command Center (1000 concurrent users)
  - Load test for Lobby Room (1000 concurrent users)
  - P95 response time <2s
  - Error rate <0.1%
- **References:** New `tests/load/command_center_load.py`, `lobby_load.py` files

#### 64. Setup Lighthouse CI
- **Phase:** 3
- **Area:** QA
- **Definition of Done:**
  - Lighthouse CI runs on every PR
  - Enforces score 90+ for performance, accessibility, best practices
  - Fails build if scores drop below threshold
- **References:** CI configuration

#### 65. Setup Percy visual regression testing
- **Phase:** 3
- **Area:** QA
- **Definition of Done:**
  - Percy snapshots for Command Center and Lobby Room
  - Visual diffs reviewed on every PR
  - Baseline approved and locked
- **References:** CI configuration

### Backend - Performance

#### 66. Database query optimization
- **Phase:** 3
- **Area:** Services
- **Definition of Done:**
  - Django Debug Toolbar analysis completed
  - N+1 queries eliminated with select_related/prefetch_related
  - All queries <100ms on production data volume
- **References:** All service files

#### 67. Implement Redis caching
- **Phase:** 3
- **Area:** Services
- **Definition of Done:**
  - Roster cached with key `lobby:roster:{tournament_id}`, TTL 60s
  - Dashboard stats cached with key `organizer:stats:{tournament_id}`, TTL 60s
  - Announcements cached with key `lobby:announcements:{tournament_id}`, TTL 300s
  - Cache invalidation in services on state changes
  - Cache hit rate 80%+
- **References:** `apps/tournaments/services/lobby_service.py`, `organizer.py`

#### 68. CDN configuration for static assets
- **Phase:** 3
- **Area:** Infra
- **Definition of Done:**
  - CloudFront (or equivalent) configured for /static/ and /media/
  - Cache headers set correctly (1 year for versioned assets)
  - Serving from CDN verified in production

### Backend - Guardrails

#### 69. Implement rate limiting
- **Phase:** 3
- **Area:** Services
- **Definition of Done:**
  - django-ratelimit configured
  - 100 requests/minute per user for AJAX endpoints
  - 10 requests/minute for bulk actions
  - Rate limit exceeded returns 429 with retry-after header
- **References:** All AJAX view endpoints

#### 70. Setup Sentry error tracking
- **Phase:** 3
- **Area:** Infra
- **Definition of Done:**
  - Sentry integrated for backend (Django) and frontend (JavaScript)
  - Error grouping configured
  - Alert rules for critical errors (500s, ValidationError spikes)
  - Team notified via Slack
- **References:** Django settings, base template

#### 71. Setup APM monitoring
- **Phase:** 3
- **Area:** Infra
- **Definition of Done:**
  - APM tool configured (New Relic, DataDog, or Elastic APM)
  - Tracks slow queries (>100ms), slow endpoints (>500ms)
  - Dashboards created for Command Center and Lobby Room
  - Alerts configured for performance degradation

#### 72. Setup alerting
- **Phase:** 3
- **Area:** Infra
- **Definition of Done:**
  - Critical alerts: 500 errors, WebSocket disconnects, Redis downtime → PagerDuty
  - Warning alerts: Slow queries, high error rates → Slack
  - Escalation policy defined

### Documentation

#### 73. Write user documentation
- **Phase:** 3
- **Area:** QA
- **Definition of Done:**
  - `docs/guides/ORGANIZER_COMMAND_CENTER.md` - How to use Command Center
  - `docs/guides/PARTICIPANT_LOBBY.md` - How to use Lobby Room
  - Screenshots and step-by-step instructions
  - Published to internal wiki

#### 74. Write developer documentation
- **Phase:** 3
- **Area:** Services
- **Definition of Done:**
  - `docs/development/SERVICE_LAYER_PATTERNS.md` - How to write services
  - `docs/api/TOURNAMENT_API.md` - API reference for endpoints
  - Code examples and best practices
  - Onboarding checklist for new developers

#### 75. Create video walkthroughs
- **Phase:** 3
- **Area:** QA
- **Definition of Done:**
  - "Using the Command Center" video (5 min) - screen recording with voiceover
  - "Checking In and Submitting Results" video (3 min)
  - Videos published to internal training portal
  - Linked from user documentation

---

## BACKLOG SUMMARY

**Total Items:** 75  
**Phase 0:** 25 items (Services + View Refactoring)  
**Phase 1:** 20 items (Command Center MVP)  
**Phase 2:** 17 items (Lobby Room vNext)  
**Phase 3:** 15 items (Automation & Polish)

**Estimated Timeline:**
- Phase 0: 2-3 weeks
- Phase 1: 2-3 weeks
- Phase 2: 2-3 weeks
- Phase 3: 1-2 weeks
- **Total: 8-10 weeks**

---

**End of Backlog**
