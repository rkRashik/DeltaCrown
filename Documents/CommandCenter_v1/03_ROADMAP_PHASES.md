# 03_ROADMAP_PHASES.md

**Initiative:** DeltaCrown Command Center + Lobby Room v1  
**Date:** December 19, 2025  
**Status:** Roadmap Definition

---

## OVERVIEW

**Total Duration:** 8-10 weeks  
**Team:** 1 backend dev, 1 frontend dev, 1 QA engineer  
**Architecture:** Django Templates + Tailwind + Vanilla JS (no React)

---

## PHASE 0: SERVICE LAYER REFACTOR

**Duration:** 2-3 weeks  
**Owner:** Backend Developer  
**Focus:** Refactor organizer views to use service layer (eliminate direct ORM mutations)

### Goals

1. **Eliminate Direct ORM Writes in Organizer Views**
   - All state changes must go through service methods
   - No `.save()` or `.update()` calls in view functions
   - Match the pattern established in `checkin.py` and `lobby.py`

2. **Complete Incomplete Implementations**
   - Finish result submission flow (remove TODO comments)
   - Finish dispute submission flow (remove TODO comments)
   - Integrate with backend APIs where planned

3. **Add Missing Service Methods**
   - `RegistrationService.approve()`, `.reject()`, `.bulk_approve()`, `.bulk_reject()`
   - `PaymentService.verify()`, `.reject()`
   - `MatchService.reschedule()`, `.forfeit()`, `.cancel()`, `.override_score()`
   - `MatchService.confirm_result()`, `.reject_result()`, `.override_result()`
   - `DisputeService.create_dispute()`, `.resolve_dispute()`

4. **Implement Side Effects**
   - Email notifications for all actions
   - Audit logging (who, what, when)
   - Webhook dispatch for external integrations

### Scope

**Files to Refactor:**
- `apps/tournaments/views/organizer.py` (1484 lines)
  - `approve_registration()` → call `RegistrationService.approve()`
  - `reject_registration()` → call `RegistrationService.reject()`
  - `bulk_approve_registrations()` → call `RegistrationService.bulk_approve()`
  - `bulk_reject_registrations()` → call `RegistrationService.bulk_reject()`
  - `verify_payment()` → call `PaymentService.verify()`
  - `reject_payment()` → call `PaymentService.reject()`
  - `toggle_checkin()` → call `CheckInService.toggle()` (create method)
  - `reschedule_match()` → call `MatchService.reschedule()`
  - `forfeit_match()` → call `MatchService.forfeit()`
  - `override_match_score()` → call `MatchService.override_score()`
  - `cancel_match()` → call `MatchService.cancel()`

- `apps/tournaments/views/organizer_results.py` (261 lines)
  - `confirm_match_result()` → call `MatchService.confirm_result()`
  - `reject_match_result()` → call `MatchService.reject_result()`
  - `override_match_result()` → call `MatchService.override_result()`

- `apps/tournaments/views/result_submission.py` (200 lines)
  - `submit_result()` → call `MatchService.submit_result()`
  - `report_dispute()` → call `DisputeService.create_dispute()`

**Service Files to Create/Enhance:**
- `apps/tournaments/services/registration_service.py`
- `apps/tournaments/services/payment_service.py`
- `apps/tournaments/services/match_service.py`
- `apps/tournaments/services/dispute_service.py`
- `apps/tournaments/services/notification_service.py` (email dispatch)
- `apps/tournaments/services/audit_service.py` (audit logging)

**Testing:**
- Unit tests for all new/modified service methods
- Integration tests for refactored view functions
- Regression tests to ensure existing functionality unchanged

### Out of Scope

- ❌ UI changes (keep existing templates)
- ❌ Real-time updates (polling/WebSockets)
- ❌ New features beyond refactoring
- ❌ Tournament creation/editing flows
- ❌ Public spectator views

### Completion Criteria

- [ ] All 20+ organizer actions delegate to service methods
- [ ] Zero `.save()` or `.update()` calls in view functions (read-only ORM queries allowed)
- [ ] All TODO comments in result_submission.py and organizer_results.py removed
- [ ] 100% unit test coverage for new service methods
- [ ] Email notifications sent for all state changes
- [ ] Audit logs created for all organizer actions
- [ ] All existing integration tests pass
- [ ] Code review approved by tech lead
- [ ] Deployed to staging and validated

### Success Metrics

- Service layer adoption: 95%+ (up from 5%)
- Test coverage: 80%+ for service layer
- Zero regressions in existing functionality
- Email notifications working for 100% of actions

---

## PHASE 1: COMMAND CENTER MVP

**Duration:** 2-3 weeks  
**Owner:** Frontend Developer  
**Focus:** Build unified organizer dashboard with Tailwind CSS

### Goals

1. **Unified Organizer Dashboard**
   - Single-page Command Center for tournament management
   - Consolidate fragmented pages into cohesive interface
   - Responsive design (desktop, tablet, mobile)

2. **Core Organizer Workflows**
   - Registration management (approve, reject, bulk actions)
   - Payment verification
   - Match management (schedule, forfeit, override)
   - Result confirmation
   - Dispute resolution

3. **Professional UI/UX**
   - Tailwind CSS design system
   - Consistent color scheme and typography
   - Accessible (WCAG 2.1 AA)
   - Fast page loads (<2s)

4. **Auto-Refresh Lists**
   - Pending registrations auto-refresh (HTMX polling)
   - Pending results auto-refresh
   - Open disputes auto-refresh

### Scope

**New Templates:**
- `templates/tournaments/organizer/command_center.html` - Main dashboard
- `templates/tournaments/organizer/_registrations_widget.html` - HTMX partial
- `templates/tournaments/organizer/_results_widget.html` - HTMX partial
- `templates/tournaments/organizer/_disputes_widget.html` - HTMX partial
- `templates/tournaments/organizer/_stats_cards.html` - Dashboard stats

**Tailwind Components:**
- `static/css/components/command_center.css` - Custom components
- Button styles (primary, secondary, danger)
- Card styles (stat cards, list cards)
- Table styles (responsive, sortable)
- Modal styles (confirmation dialogs)

**JavaScript Modules:**
- `static/js/command_center/registration_actions.js` - Approve/reject/bulk
- `static/js/command_center/result_actions.js` - Confirm/reject/override
- `static/js/command_center/dispute_actions.js` - Resolve disputes
- `static/js/command_center/notifications.js` - Toast notifications
- `static/js/command_center/modals.js` - Confirmation dialogs

**Views (Refactored):**
- `OrganizerDashboardView` - Main dashboard view
- `RegistrationActionsView` - AJAX endpoints for registration actions
- `ResultActionsView` - AJAX endpoints for result actions
- `DisputeActionsView` - AJAX endpoints for dispute actions

**Features:**
- Stats cards (total registrations, checked in, pending results, open disputes)
- Pending registrations list with approve/reject buttons
- Pending results list with confirm/reject buttons
- Open disputes list with resolve button
- Bulk actions (select multiple, approve/reject all)
- Inline actions (approve/reject without page reload)
- Toast notifications (success/error messages)
- Confirmation modals (prevent accidental actions)

### Out of Scope

- ❌ Real-time updates via WebSockets (Phase 2)
- ❌ Advanced analytics/charts
- ❌ Tournament creation/editing UI
- ❌ Bracket editing UI
- ❌ Advanced filtering/sorting (basic only)
- ❌ Participant-facing features

### Completion Criteria

- [ ] Unified Command Center dashboard accessible at `/tournaments/<slug>/organizer/`
- [ ] All core organizer actions work via AJAX (no full page reloads)
- [ ] Auto-refresh lists update every 10 seconds (HTMX polling)
- [ ] Responsive design works on desktop (1920px), tablet (768px), mobile (375px)
- [ ] All actions show toast notifications (success/error)
- [ ] Confirmation modals for destructive actions (reject, cancel, override)
- [ ] WCAG 2.1 AA compliance verified
- [ ] Page load time <2s on staging
- [ ] Cross-browser testing passed (Chrome, Firefox, Safari, Edge)
- [ ] QA approval and organizer user acceptance testing passed

### Success Metrics

- Organizer task completion time reduced by 30%
- 90%+ organizer satisfaction score
- Zero accessibility violations
- <2s page load time
- <200ms AJAX response time

---

## PHASE 2: LOBBY ROOM vNEXT

**Duration:** 2-3 weeks  
**Owner:** Frontend Developer  
**Focus:** Enhance participant lobby with real-time updates and complete workflows

### Goals

1. **Real-Time Roster Updates**
   - Live check-in status updates
   - WebSocket-based updates (not polling)
   - Instant visibility when participants check in

2. **Complete Result Submission Flow**
   - Remove TODO comments from result_submission.py
   - Full integration with MatchService
   - Evidence upload (screenshots, video links)
   - Opponent confirmation workflow

3. **Complete Dispute Submission Flow**
   - Remove TODO comments from disputes_management.py
   - Full integration with DisputeService
   - Evidence upload
   - Organizer notification

4. **Enhanced Lobby Hub**
   - Tournament announcements (organizer posts)
   - Match schedule display
   - Next match countdown
   - Live match status updates

### Scope

**Real-Time Infrastructure:**
- Django Channels setup (WebSocket support)
- Redis for channel layer
- `consumers/lobby_consumer.py` - WebSocket consumer for lobby events
- Service integration: services dispatch WebSocket events on state changes

**New Templates:**
- `templates/tournaments/lobby/hub_v2.html` - Enhanced lobby hub
- `templates/tournaments/lobby/_announcements.html` - Announcements widget
- `templates/tournaments/lobby/_next_match.html` - Next match widget
- `templates/tournaments/matches/submit_result.html` - Complete result submission form
- `templates/tournaments/matches/dispute_form.html` - Complete dispute form

**JavaScript Modules:**
- `static/js/lobby/websocket_client.js` - WebSocket connection management
- `static/js/lobby/roster_updates.js` - Handle roster update events
- `static/js/lobby/announcements.js` - Handle announcement events
- `static/js/matches/result_submission.js` - Result submission form
- `static/js/matches/dispute_submission.js` - Dispute submission form

**Service Methods (Complete Implementation):**
- `MatchService.submit_result()` - Participant submits result
- `MatchService.confirm_opponent_result()` - Opponent confirms
- `DisputeService.create_dispute()` - Participant creates dispute
- `DisputeService.attach_evidence()` - Upload evidence
- `LobbyService.post_announcement()` - Organizer posts announcement
- `LobbyService.get_next_match()` - Get participant's next match

**WebSocket Events:**
- `roster.updated` - Roster changed (check-in, registration)
- `announcement.new` - New announcement posted
- `match.updated` - Match status changed
- `result.submitted` - Result submitted by participant
- `dispute.created` - Dispute created

### Out of Scope

- ❌ Voice chat integration
- ❌ In-app chat messaging
- ❌ Advanced match lobbies (Discord integration)
- ❌ Spectator mode features
- ❌ Leaderboard/rankings

### Completion Criteria

- [ ] WebSocket connection established on lobby page load
- [ ] Roster updates in real-time when participants check in (no page refresh)
- [ ] Announcements appear instantly when organizer posts
- [ ] Result submission form fully functional with evidence upload
- [ ] Dispute submission form fully functional with evidence upload
- [ ] All TODO comments removed from result_submission.py and disputes_management.py
- [ ] WebSocket reconnection logic working (handles disconnects)
- [ ] Graceful degradation if WebSockets unavailable (fallback to polling)
- [ ] Redis configured in staging/production
- [ ] Load testing passed (100 concurrent WebSocket connections)
- [ ] QA approval and participant user acceptance testing passed

### Success Metrics

- Real-time updates: <1s latency
- WebSocket connection stability: 99%+ uptime
- Result submission completion rate: 90%+
- Participant satisfaction score: 85%+
- Zero critical bugs in result/dispute workflows

---

## PHASE 3: AUTOMATION & POLISH

**Duration:** 1-2 weeks  
**Owner:** Backend Developer + Frontend Developer  
**Focus:** Automation, testing, performance, guardrails

### Goals

1. **Automated Testing Suite**
   - End-to-end tests for critical workflows
   - Load testing for Command Center and Lobby Room
   - Accessibility testing automation
   - Visual regression testing

2. **Performance Optimization**
   - Database query optimization (N+1 query detection)
   - Caching strategy (Redis for roster, stats)
   - CDN for static assets
   - Image optimization

3. **Guardrails & Monitoring**
   - Rate limiting for AJAX endpoints
   - Error tracking (Sentry integration)
   - Performance monitoring (APM)
   - Alerting for critical failures

4. **Documentation & Training**
   - User documentation (organizer guide, participant guide)
   - Developer onboarding docs
   - API documentation
   - Video walkthroughs

### Scope

**Automated Testing:**
- Cypress E2E tests for organizer workflows
- Cypress E2E tests for participant workflows
- Locust load tests (1000 concurrent users)
- Lighthouse CI for performance/accessibility
- Percy visual regression tests

**Performance:**
- Database query analysis (Django Debug Toolbar)
- Add `.select_related()` and `.prefetch_related()` where missing
- Redis caching for:
  - Tournament roster (cache key: `lobby:roster:{tournament_id}`)
  - Dashboard stats (cache key: `organizer:stats:{tournament_id}`)
  - Announcements (cache key: `lobby:announcements:{tournament_id}`)
- Cache invalidation on state changes (service layer triggers)

**Guardrails:**
- Django rate limiting (django-ratelimit)
  - 100 requests/minute per user for AJAX endpoints
  - 10 requests/minute for bulk actions
- Sentry error tracking
  - Frontend error tracking (JavaScript errors)
  - Backend error tracking (500 errors, ValidationError)
- APM (Application Performance Monitoring)
  - Track slow queries (>100ms)
  - Track slow endpoints (>500ms)
- Alerts via Slack/PagerDuty
  - Critical: 500 errors, WebSocket disconnects, Redis downtime
  - Warning: Slow queries, high error rates

**Documentation:**
- `docs/guides/ORGANIZER_COMMAND_CENTER.md` - Organizer user guide
- `docs/guides/PARTICIPANT_LOBBY.md` - Participant user guide
- `docs/development/SERVICE_LAYER_PATTERNS.md` - Developer guide
- `docs/api/TOURNAMENT_API.md` - API reference
- Video walkthroughs (Loom):
  - "Using the Command Center" (5 min)
  - "Checking In and Submitting Results" (3 min)

### Out of Scope

- ❌ Advanced analytics dashboard
- ❌ Machine learning features
- ❌ Multi-language support (i18n)
- ❌ Mobile native apps

### Completion Criteria

- [ ] E2E test suite covers 90%+ of user workflows
- [ ] Load testing passed: 1000 concurrent users, <2s response time
- [ ] Lighthouse score: 90+ for performance, accessibility, best practices
- [ ] Zero N+1 queries detected in critical paths
- [ ] Cache hit rate: 80%+ for roster/stats queries
- [ ] Rate limiting active on all AJAX endpoints
- [ ] Sentry error tracking configured and tested
- [ ] APM dashboards created and alerting configured
- [ ] All documentation complete and reviewed
- [ ] Video walkthroughs published
- [ ] Security audit passed (OWASP top 10 check)
- [ ] Final QA sign-off and production deployment approval

### Success Metrics

- E2E test coverage: 90%+
- Load test success: 1000 users, <2s p95 response time
- Lighthouse score: 90+ across all metrics
- Cache hit rate: 80%+
- Error rate: <0.1% of requests
- Uptime: 99.9%+
- Documentation completeness: 100%

---

## DEPENDENCIES & RISKS

### Cross-Phase Dependencies

**Phase 1 depends on Phase 0:**
- Command Center UI requires refactored service layer
- Cannot build UI on top of direct ORM mutations

**Phase 2 depends on Phase 1:**
- Lobby Room enhancements build on patterns from Command Center
- WebSocket infrastructure reusable across both

**Phase 3 depends on Phase 0-2:**
- Testing requires complete implementation
- Performance optimization requires full system

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Service refactor breaks existing functionality | HIGH | Comprehensive regression testing, feature flags |
| WebSocket infrastructure complexity | MEDIUM | Start with polling fallback, gradual rollout |
| Performance issues with real-time updates | MEDIUM | Load testing early, caching strategy |
| Browser compatibility issues | LOW | Cross-browser testing, progressive enhancement |
| Django Channels learning curve | MEDIUM | Spike work in Phase 1, external consultation if needed |

### Schedule Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Phase 0 takes longer than expected | HIGH | Prioritize critical functions first, defer nice-to-haves |
| Frontend developer availability | MEDIUM | Prepare detailed designs upfront, consider contractor |
| QA bandwidth constraints | MEDIUM | Automate testing, parallel QA during development |
| Production deployment delays | LOW | Staging deployment early, incremental rollout |

---

## ROLLOUT STRATEGY

### Phase 0 Rollout
- Deploy to staging after each function refactored
- Organizer team beta testing (5-10 users)
- Rollback plan: feature flags for new service calls
- Production deployment: gradual rollout (10% → 50% → 100%)

### Phase 1 Rollout
- Deploy Command Center to staging
- Organizer team alpha testing (2-3 users)
- Organizer team beta testing (10-15 users)
- Production deployment: opt-in beta (organizers can choose new UI)
- Monitor metrics: task completion time, error rates
- Full rollout after 1 week beta period

### Phase 2 Rollout
- Deploy Lobby Room to staging
- Participant beta testing (50-100 users)
- Monitor WebSocket connection stability
- Production deployment: gradual rollout (10% → 50% → 100%)
- Fallback to polling if WebSocket issues detected

### Phase 3 Rollout
- Continuous deployment of testing/monitoring improvements
- Documentation published incrementally
- No user-facing changes (internal tooling)

---

## SUCCESS CRITERIA (Overall)

### Technical Metrics

- [ ] Service layer adoption: 95%+ (all state changes through services)
- [ ] Test coverage: 80%+ (service layer), 70%+ (views)
- [ ] Lighthouse score: 90+ (performance, accessibility, best practices)
- [ ] Page load time: <2s (p95)
- [ ] AJAX response time: <200ms (p95)
- [ ] WebSocket latency: <1s (p95)
- [ ] Uptime: 99.9%+
- [ ] Error rate: <0.1% of requests

### User Metrics

- [ ] Organizer satisfaction: 90%+ (NPS score)
- [ ] Participant satisfaction: 85%+ (NPS score)
- [ ] Task completion rate: 95%+ (organizer workflows)
- [ ] Result submission rate: 90%+ (participant workflows)
- [ ] Support ticket volume: -50% (fewer usability issues)

### Business Metrics

- [ ] Organizer task completion time: -30% (faster workflows)
- [ ] Tournament launch time: -20% (less manual setup)
- [ ] Active tournaments: +25% (better organizer experience)
- [ ] Participant retention: +15% (better participant experience)

---

## POST-LAUNCH

### Monitoring Period (2 weeks)

- Daily metrics review
- Weekly retrospective
- User feedback collection (surveys, interviews)
- Bug triage and hot fixes
- Performance tuning based on real traffic

### Iteration Planning (Week 3+)

- Prioritize top user requests
- Address technical debt identified during implementation
- Plan Phase 4 features:
  - Advanced analytics
  - Bracket editing UI
  - Mobile app (React Native)
  - Multi-language support

---

**End of Roadmap**
