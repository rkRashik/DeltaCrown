# TRACKER_DECISIONS.md

**Initiative:** DeltaCrown Command Center + Lobby Room v1  
**Date:** December 19, 2025  
**Purpose:** Architecture Decision Records (ADRs)

---

## ADR-001: Django Templates + Tailwind + Vanilla JS (No React/Next.js)

**Date:** December 19, 2025  
**Status:** Accepted  
**Deciders:** Backend Dev Lead, Frontend Dev Lead, Tech Lead

### Decision

Use Django Templates with Tailwind CSS and Vanilla JavaScript for all Command Center and Lobby Room interfaces. Do NOT migrate to React, Next.js, or other JavaScript frameworks.

### Rationale

1. **Existing Stack Consistency:** DeltaCrown platform already uses Django templates throughout. Introducing React would create two separate frontend architectures.

2. **Server-Side Rendering Benefits:** Django templates provide fast initial page loads, SEO-friendly HTML, and simpler caching strategies.

3. **Team Expertise:** Current team is proficient in Django template development. React would require hiring or training.

4. **No Build Step Required:** Vanilla JS eliminates webpack/vite build complexity, faster development iteration.

5. **Progressive Enhancement:** Can add JavaScript interactivity incrementally without framework lock-in.

6. **Maintenance Simplicity:** Single language (Python) for backend + templates reduces context switching.

### Consequences

**Positive:**
- ✅ Faster development (no React learning curve)
- ✅ Simpler deployment (no build artifacts)
- ✅ Better SEO (server-rendered HTML)
- ✅ Lower complexity (no state management libraries)
- ✅ Easier testing (standard Django test tools)

**Negative:**
- ❌ Less dynamic UIs (more full page reloads)
- ❌ Limited component reusability across pages
- ❌ Manual DOM manipulation in JavaScript (no virtual DOM)
- ❌ Harder to build complex interactive features

**Mitigation:**
- Use HTMX for partial page updates (reduces full page reloads)
- Create reusable Django template includes for common components
- Use Tailwind CSS for consistent styling without React component libraries

### Compliance

All new frontend work MUST use Django templates. React is prohibited for this initiative.

---

## ADR-002: Views Are Thin Controllers (No ORM Mutations)

**Date:** December 19, 2025  
**Status:** Accepted  
**Deciders:** Backend Dev Lead, Tech Lead

### Decision

All Django views MUST delegate business logic to service layer methods. Views are thin controllers responsible for HTTP concerns only. Views MUST NOT call `.save()` or `.update()` on model instances.

### Rationale

1. **Current Anti-Pattern Identified:** Audit revealed 95% of organizer views bypass service layer and manipulate ORM directly (see 04_VIEW_TO_SERVICE_CALLMAP.md).

2. **Missing Side Effects:** Direct ORM writes skip email notifications, audit logging, validation, and tournament_ops integration.

3. **Untestable Code:** Business logic in views requires mocking Django ORM, making unit tests fragile and slow.

4. **Code Duplication:** Same logic (e.g., registration approval) implemented differently in multiple views.

5. **Consistency with Best Practices:** Participant views (checkin.py, lobby.py) already follow this pattern with 89-100% service adoption.

### Consequences

**Positive:**
- ✅ Testable business logic (service unit tests without ORM mocking)
- ✅ Consistent side effects (emails, logs, webhooks always triggered)
- ✅ Reusable logic (services called from views, APIs, tasks, management commands)
- ✅ tournament_ops integration points reachable
- ✅ Easier debugging (business logic centralized in service layer)

**Negative:**
- ❌ Requires refactoring 20+ existing view functions (Phase 0 scope)
- ❌ Steeper learning curve for new developers (must learn service patterns)
- ❌ Extra indirection layer (view → service → ORM)

**Mitigation:**
- Comprehensive refactoring plan in Phase 0 (04_BACKLOG.md items #1-25)
- Developer documentation: SERVICE_LAYER_PATTERNS.md
- Code review checklist enforces pattern
- Use checkin.py and lobby.py as reference implementations

### Compliance

All PRs touching tournament views MUST:
- [ ] No `.save()` or `.update()` calls in view functions
- [ ] All state changes delegate to service methods
- [ ] Service methods have unit tests
- [ ] ValidationError properly handled in views

---

## ADR-003: tournament_ops Integration Only Via Services

**Date:** December 19, 2025  
**Status:** Accepted  
**Deciders:** Backend Dev Lead, tournament_ops Maintainer, Tech Lead

### Decision

Views and templates MUST NOT import or call tournament_ops modules directly. All tournament_ops integration MUST go through `apps/tournaments/services/` layer.

### Rationale

1. **Clean Separation of Concerns:** tournament_ops is headless orchestration layer, should be isolated from web layer.

2. **DTO Contract Enforcement:** Services transform Django models to tournament_ops DTOs, ensuring clean interface contracts.

3. **Error Translation:** Services translate tournament_ops exceptions to Django ValidationError for view layer.

4. **Current Bypass Problem:** Organizer views manipulate ORM directly, never reaching tournament_ops integration points in services.

5. **Testing Isolation:** Services can mock tournament_ops calls; views should not need to know about tournament_ops.

### Consequences

**Positive:**
- ✅ Clean architectural boundaries (web layer ↔ service layer ↔ tournament_ops)
- ✅ Easier to refactor tournament_ops without touching views
- ✅ DTO contracts validated in services (type safety)
- ✅ Consistent error handling across all tournament_ops calls

**Negative:**
- ❌ Extra indirection (view → service → tournament_ops)
- ❌ Services must handle DTO transformation (more boilerplate)
- ❌ Developers must understand 3 layers instead of 2

**Mitigation:**
- Document tournament_ops integration patterns in SERVICE_LAYER_PATTERNS.md
- Provide DTO transformation examples in existing services (BracketService, StageTransitionService)
- Code review enforces no direct tournament_ops imports in views

### Compliance

Forbidden in views:
```python
# ❌ NEVER do this
from apps.tournament_ops.services.bracket_engine_service import BracketEngineService
```

Required pattern:
```python
# ✅ ALWAYS do this
from apps.tournaments.services.bracket_service import BracketService
bracket = BracketService.generate_bracket(tournament)
```

---

## ADR-004: Real-Time Updates - HTMX Polling First, WebSockets Later

**Date:** December 19, 2025  
**Status:** Accepted  
**Deciders:** Frontend Dev Lead, Backend Dev Lead, Tech Lead

### Decision

**Phase 1 (Command Center MVP):** Use HTMX polling (10-second intervals) for auto-refresh lists (pending registrations, pending results, open disputes).

**Phase 2 (Lobby Room vNext):** Upgrade to WebSockets (Django Channels) for real-time roster updates, announcements, and match status.

### Rationale

1. **Incremental Complexity:** HTMX polling is simpler to implement and requires no additional infrastructure. WebSockets require Django Channels + Redis.

2. **Fast MVP Delivery:** Phase 1 can ship without WebSocket infrastructure, reducing Phase 1 timeline by ~1 week.

3. **Graceful Degradation:** HTMX polling works in all browsers and network conditions. WebSockets can fall back to polling if connection fails.

4. **Different Use Cases:** 
   - Command Center: Organizers checking pending items (polling acceptable, low traffic)
   - Lobby Room: Participants watching live roster (WebSockets better UX, high traffic)

5. **Risk Mitigation:** If WebSocket implementation proves too complex in Phase 2, can continue with polling without blocking launch.

### Consequences

**Phase 1 - HTMX Polling:**

**Positive:**
- ✅ Simple implementation (HTMX attribute: `hx-trigger="every 10s"`)
- ✅ No additional infrastructure (Redis, Django Channels)
- ✅ Works in all browsers, no compatibility issues
- ✅ Easy to debug (standard HTTP requests)

**Negative:**
- ❌ Not truly real-time (10-second delay)
- ❌ Increased server load (polling every 10s per user)
- ❌ Unnecessary requests if no data changed

**Phase 2 - WebSockets:**

**Positive:**
- ✅ True real-time updates (<1s latency)
- ✅ Efficient (push, not poll)
- ✅ Better UX for high-traffic scenarios (lobby roster)

**Negative:**
- ❌ Infrastructure complexity (Django Channels, Redis channel layer)
- ❌ Stateful connections (scaling challenges)
- ❌ Browser compatibility (need fallback to polling)
- ❌ Learning curve for team

**Mitigation:**
- Phase 1 polling serves as fallback if Phase 2 WebSockets fail
- Load testing in Phase 2 to validate WebSocket performance
- Spike work on Django Channels before Phase 2 kickoff
- Budget for external consultation if needed

### Compliance

**Phase 1 Implementation:**
```django
{# HTMX polling pattern #}
<div id="pending-registrations"
     hx-get="{% url 'tournaments:organizer_registrations_partial' tournament.slug %}"
     hx-trigger="every 10s"
     hx-swap="innerHTML">
    {# Content auto-refreshes every 10 seconds #}
</div>
```

**Phase 2 Implementation:**
```javascript
// WebSocket pattern
const socket = new WebSocket(`ws://localhost:8000/ws/lobby/${tournamentSlug}/`);
socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'roster.updated') {
        updateRosterDOM(data.roster_data);
    }
};
```

---

## ADR-005: Service Methods Must Handle All Side Effects

**Date:** December 19, 2025  
**Status:** Accepted  
**Deciders:** Backend Dev Lead, QA Lead, Tech Lead

### Decision

Every service method that changes tournament state MUST handle ALL side effects within the method: email notifications, audit logging, webhook dispatch, cache invalidation, WebSocket events (Phase 2+).

Views MUST NOT implement side effects. Views only handle HTTP concerns (request parsing, response formatting, authentication/authorization).

### Rationale

1. **Current Gap:** Direct ORM writes in views skip all side effects (no emails, no audit logs, no webhooks).

2. **Consistency Guarantee:** If side effects live in services, they fire 100% of the time regardless of call origin (view, API, Celery task, management command).

3. **Single Responsibility:** Service owns business logic AND its side effects. View owns HTTP concerns only.

4. **Testing:** Service tests verify side effects (assert email sent, audit log created). View tests don't need to test side effects.

### Consequences

**Positive:**
- ✅ Side effects never missed (emails always sent when registration approved)
- ✅ Consistent behavior across all entry points (views, APIs, tasks)
- ✅ Service tests verify complete business logic including side effects
- ✅ Views remain thin and focused on HTTP concerns

**Negative:**
- ❌ Service methods more complex (more responsibilities)
- ❌ Service tests must mock email sending, webhook dispatch
- ❌ Longer service method execution time (side effects add latency)

**Mitigation:**
- Use @transaction.atomic to ensure side effects happen only if state change succeeds
- Delegate to dedicated services (EmailService, AuditService, WebhookService) to keep methods readable
- Consider async tasks (Celery) for slow side effects (email sending) in future optimization

### Compliance

**Required Service Pattern:**
```python
@staticmethod
@transaction.atomic
def approve(registration: Registration, approved_by: User) -> Registration:
    # 1. Validation
    if registration.status != Registration.PENDING:
        raise ValidationError("Only pending registrations can be approved")
    
    # 2. State change
    registration.status = Registration.CONFIRMED
    registration.approved_by = approved_by
    registration.approved_at = timezone.now()
    registration.save()
    
    # 3. Side effects (ALL must be handled here)
    EmailService.send_registration_confirmed(registration)  # Email
    AuditLog.create(action='registration_approved', user=approved_by, target=registration)  # Audit
    WebhookDispatcher.dispatch('registration.approved', registration)  # Webhook
    cache.delete(f'lobby:roster:{registration.tournament.id}')  # Cache invalidation
    
    # 4. Return
    return registration
```

**Forbidden View Pattern:**
```python
# ❌ NEVER implement side effects in views
def approve_registration(request, registration_id):
    registration = get_object_or_404(Registration, id=registration_id)
    approved = RegistrationService.approve(registration, request.user)
    
    # ❌ Side effects should be in service, not here
    send_email(registration.user.email, "Registration Approved")  # WRONG
    
    return JsonResponse({'success': True})
```

---

## ADR-006: Gradual Rollout with Feature Flags

**Date:** December 19, 2025  
**Status:** Accepted  
**Deciders:** Backend Dev Lead, DevOps Lead, Product Manager

### Decision

All phases MUST deploy with gradual rollout strategy using feature flags. Phase 0 (service refactor) uses feature flags to control service usage. Phase 1 (Command Center UI) uses feature flags for opt-in beta.

### Rationale

1. **Risk Mitigation:** Service refactor touches 20+ critical organizer functions. Gradual rollout reduces blast radius if bugs occur.

2. **Rollback Safety:** Feature flags allow instant rollback without redeploying code.

3. **A/B Testing:** Can measure task completion time before/after with gradual rollout (10% → 50% → 100%).

4. **Beta Testing:** Organizers can opt into new Command Center UI while others stay on old UI during Phase 1 beta period.

5. **Monitoring Window:** Gradual rollout gives time to monitor error rates, performance metrics before full deployment.

### Consequences

**Positive:**
- ✅ Safe rollout (bugs affect small % of users initially)
- ✅ Instant rollback (toggle flag off, no redeploy)
- ✅ Data-driven decisions (compare metrics across cohorts)
- ✅ Beta testing without forcing all users to new UI

**Negative:**
- ❌ Code complexity (if/else branches based on flags)
- ❌ Need feature flag infrastructure (LaunchDarkly, Django-Waffle, or custom)
- ❌ Must maintain both old and new code paths during rollout
- ❌ Flag cleanup required after full rollout (tech debt)

**Mitigation:**
- Use simple feature flag library (django-waffle recommended)
- Document flag lifecycle (when to create, when to remove)
- Schedule flag cleanup in Phase 3 (after full rollout confirmed stable)

### Compliance

**Phase 0 Feature Flag Example:**
```python
from waffle import flag_is_active

def approve_registration(request, tournament_id, registration_id):
    registration = get_object_or_404(Registration, id=registration_id)
    
    if flag_is_active(request, 'use_registration_service'):
        # New service-based approach
        try:
            approved = RegistrationService.approve(registration, request.user)
            return JsonResponse({'success': True})
        except ValidationError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    else:
        # Old direct ORM approach (fallback during rollout)
        registration.status = 'confirmed'
        registration.save()
        return JsonResponse({'success': True})
```

**Phase 1 Feature Flag Example:**
```python
# Organizer can choose which UI to use
def organizer_dashboard(request, slug):
    tournament = get_object_or_404(Tournament, slug=slug)
    
    if flag_is_active(request, 'command_center_v2'):
        # New Command Center UI
        return render(request, 'tournaments/organizer/command_center.html', context)
    else:
        # Old organizer dashboard
        return render(request, 'tournaments/organizer/dashboard_v1.html', context)
```

**Rollout Schedule:**
- Week 1: 10% of organizers (flag enabled for 10%)
- Week 2: 50% of organizers (monitor metrics)
- Week 3: 100% rollout (if no issues)
- Week 4: Remove flag, delete old code path

---

## DECISION SUMMARY

| ADR | Decision | Status | Phase |
|-----|----------|--------|-------|
| ADR-001 | Django Templates (No React) | Accepted | All |
| ADR-002 | Views Are Thin Controllers | Accepted | Phase 0+ |
| ADR-003 | tournament_ops Only Via Services | Accepted | Phase 0+ |
| ADR-004 | HTMX Polling → WebSockets | Accepted | Phase 1 → Phase 2 |
| ADR-005 | Services Handle All Side Effects | Accepted | Phase 0+ |
| ADR-006 | Gradual Rollout with Feature Flags | Accepted | All Phases |

---

## PENDING DECISIONS

**None at this time.**

Future decisions to be documented:
- Caching strategy (Redis keys, TTLs, invalidation) - Phase 3
- Rate limiting configuration - Phase 3
- APM tool selection (New Relic vs DataDog vs Elastic) - Phase 3
- WebSocket scaling strategy (horizontal vs vertical) - Phase 2

---

**Last Updated:** December 19, 2025
