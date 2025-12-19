# 02_TARGET_ARCHITECTURE_TEMPLATES_FIRST.md

**Initiative:** DeltaCrown Command Center + Lobby Room v1  
**Date:** December 19, 2025  
**Status:** Architecture Definition

---

## 1. ARCHITECTURE OVERVIEW

**Philosophy:** Server-rendered templates with progressive enhancement. No JavaScript frameworks. Business logic lives in services, not views or templates.

**Frontend Stack:**
- **Django Templates** - Server-side rendering, no React/Next.js
- **Tailwind CSS** - Utility-first styling, responsive design
- **Vanilla JavaScript** - Progressive enhancement, DOM manipulation
- **HTMX** (optional) - AJAX updates without heavy JS

**Backend Stack:**
- **Django Views** - Thin controllers (orchestration only)
- **Django Services** - Business logic, validation, side effects
- **Django Models** - Data persistence
- **tournament_ops** - Headless orchestration (accessed ONLY via services)

---

## 2. CORE ARCHITECTURAL PRINCIPLES

### Principle 1: Views Are Thin Controllers

**Rule:** Views orchestrate but do not implement business logic.

**Views MAY:**
- ✅ Get objects via ORM (read-only queries)
- ✅ Call service methods
- ✅ Handle HTTP concerns (authentication, authorization, response formatting)
- ✅ Render templates with context data
- ✅ Return JSON for AJAX endpoints

**Views MUST NOT:**
- ❌ Call `.save()` on model instances
- ❌ Call `.update()` on querysets
- ❌ Implement validation logic
- ❌ Send emails or notifications
- ❌ Calculate business values
- ❌ Interact with tournament_ops directly

**Example - CORRECT:**
```python
# View delegates to service
from apps.tournaments.services.registration_service import RegistrationService

def approve_registration(request, tournament_id, registration_id):
    registration = get_object_or_404(Registration, id=registration_id)
    
    try:
        # Service handles all business logic
        approved_registration = RegistrationService.approve(
            registration=registration,
            approved_by=request.user
        )
        return JsonResponse({'success': True})
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
```

**Example - INCORRECT:**
```python
# View implements business logic (ANTI-PATTERN)
def approve_registration(request, tournament_id, registration_id):
    registration = get_object_or_404(Registration, id=registration_id)
    
    # ❌ Direct ORM mutation
    registration.status = 'confirmed'
    registration.save()
    
    # ❌ Business logic in view
    # Missing: notifications, audit logs, validation
    
    return JsonResponse({'success': True})
```

---

### Principle 2: All State Changes Through Services

**Rule:** Any operation that mutates tournament data MUST go through a service method.

**State Changes Include:**
- Registration approval/rejection
- Payment verification
- Check-in operations
- Match scheduling/rescheduling
- Result submission/confirmation
- Dispute creation/resolution
- Tournament status transitions
- Bracket modifications

**Service Method Pattern:**
```python
# Service method signature
@staticmethod
@transaction.atomic
def approve(registration: Registration, approved_by: User) -> Registration:
    """
    Approve a tournament registration.
    
    Business logic:
    - Validate registration state
    - Check tournament capacity
    - Update status to CONFIRMED
    - Send confirmation email
    - Log audit trail
    - Dispatch webhook
    
    Raises:
        ValidationError: If approval is invalid
    """
    # Validation
    if registration.status not in [Registration.PENDING, Registration.PAYMENT_SUBMITTED]:
        raise ValidationError("Only pending registrations can be approved")
    
    # State change
    registration.status = Registration.CONFIRMED
    registration.approved_by = approved_by
    registration.approved_at = timezone.now()
    registration.save()
    
    # Side effects
    EmailService.send_registration_confirmed(registration)
    AuditLog.create(action='registration_approved', user=approved_by, target=registration)
    WebhookDispatcher.dispatch('registration.approved', registration)
    
    return registration
```

---

### Principle 3: Services Own Business Logic

**Rule:** Services encapsulate ALL business rules, validations, and side effects.

**Service Responsibilities:**
1. **Validation**
   - State transition rules
   - Business rule enforcement
   - Precondition checks
   - Raise `ValidationError` for invalid operations

2. **State Mutations**
   - Update model instances
   - Use `@transaction.atomic` for multi-model changes
   - Ensure data consistency

3. **Side Effects**
   - Email notifications
   - In-app notifications
   - Audit logging
   - Webhook dispatch
   - Cache invalidation
   - Search index updates

4. **Integration**
   - Call tournament_ops services when needed
   - Transform data to/from DTOs
   - Handle external API calls

5. **Return Values**
   - Return updated model instances
   - Return computed results
   - Raise exceptions for errors (don't return None on failure)

**Service Layer Structure:**
```
apps/tournaments/services/
├── registration_service.py      # Registration lifecycle
├── check_in_service.py          # Check-in operations (GOLD STANDARD)
├── lobby_service.py             # Lobby data aggregation (GOLD STANDARD)
├── match_service.py             # Match lifecycle
├── payment_service.py           # Payment processing
├── dispute_service.py           # Dispute management
├── bracket_service.py           # Bracket generation → tournament_ops
├── stage_transition_service.py  # Stage transitions → tournament_ops
└── notification_service.py      # Notification dispatch
```

---

### Principle 4: tournament_ops via Services Only

**Rule:** Views and templates NEVER interact with tournament_ops directly. Only services call tournament_ops.

**tournament_ops Integration Pattern:**
```python
# apps/tournaments/services/bracket_service.py
from apps.tournament_ops.services.bracket_engine_service import BracketEngineService
from apps.tournament_ops.dtos import BracketGenerationDTO

class BracketService:
    @staticmethod
    def generate_bracket(tournament: Tournament) -> Bracket:
        """Generate bracket structure via tournament_ops."""
        
        # Validate preconditions
        if tournament.status != Tournament.REGISTRATION_CLOSED:
            raise ValidationError("Cannot generate bracket until registration closes")
        
        # Transform to DTO
        dto = BracketGenerationDTO(
            tournament_id=tournament.id,
            format=tournament.bracket_format,
            participants=list(tournament.registrations.filter(status=Registration.CONFIRMED))
        )
        
        # Call tournament_ops
        bracket_data = BracketEngineService.generate(dto)
        
        # Create/update bracket model
        bracket, created = Bracket.objects.update_or_create(
            tournament=tournament,
            defaults={'bracket_structure': bracket_data, 'is_generated': True}
        )
        
        # Side effects
        NotificationService.notify_bracket_generated(tournament)
        
        return bracket
```

**Why This Matters:**
- tournament_ops is a shared orchestration layer
- Direct calls bypass validation and audit logging
- DTOs ensure clean interface contracts
- Services handle error translation and rollback

---

## 3. FRONTEND ARCHITECTURE

### 3.1 Django Templates

**Template Responsibilities:**
- ✅ Render HTML from context data
- ✅ Display static content and user data
- ✅ Handle form rendering
- ✅ Include Tailwind utility classes
- ✅ Attach JS event handlers (data-* attributes)

**Template MUST NOT:**
- ❌ Implement business logic in template tags
- ❌ Perform complex data transformations
- ❌ Call services directly
- ❌ Mutate database state

**Template Pattern:**
```django
{# templates/tournaments/organizer/dashboard.html #}
{% extends "base.html" %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">{{ tournament.name }} - Command Center</h1>
    
    {# Stats cards #}
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div class="bg-white rounded-lg shadow p-6">
            <h3 class="text-gray-600 text-sm font-medium">Registrations</h3>
            <p class="text-3xl font-bold">{{ stats.total_registrations }}</p>
        </div>
        {# More cards... #}
    </div>
    
    {# HTMX-powered pending registrations list #}
    <div id="pending-registrations" 
         hx-get="{% url 'tournaments:organizer_pending_registrations' tournament.slug %}"
         hx-trigger="load, every 10s">
        {# Will be replaced by HTMX response #}
        <p class="text-gray-500">Loading...</p>
    </div>
</div>
{% endblock %}
```

---

### 3.2 Tailwind CSS

**Styling Strategy:**
- Use Tailwind utility classes directly in templates
- Create reusable component classes in `static/css/components.css` for complex patterns
- Use Tailwind's responsive modifiers (`md:`, `lg:`) for responsive design
- Use Tailwind's state modifiers (`hover:`, `focus:`, `disabled:`) for interactivity

**Component Pattern:**
```css
/* static/css/components.css */
@layer components {
  .btn-primary {
    @apply px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 
           focus:outline-none focus:ring-2 focus:ring-blue-500 
           disabled:opacity-50 disabled:cursor-not-allowed;
  }
  
  .card {
    @apply bg-white rounded-lg shadow-md p-6;
  }
  
  .stat-card {
    @apply card flex flex-col items-center justify-center;
  }
}
```

**Usage in Templates:**
```django
<button class="btn-primary" data-action="approve">
    Approve Registration
</button>

<div class="card">
    <h3 class="text-lg font-semibold mb-4">{{ registration.user.username }}</h3>
    <p class="text-gray-600">Status: {{ registration.get_status_display }}</p>
</div>
```

---

### 3.3 Vanilla JavaScript

**JavaScript Responsibilities:**
- ✅ DOM manipulation
- ✅ Event handling (clicks, form submissions)
- ✅ AJAX requests to backend endpoints
- ✅ Client-side form validation (progressive enhancement)
- ✅ UI state management (modals, dropdowns, tabs)
- ✅ Real-time updates (polling or WebSocket listeners)

**JavaScript MUST NOT:**
- ❌ Implement business logic
- ❌ Perform calculations that should be server-side
- ❌ Directly manipulate models or database
- ❌ Bypass backend validation

**JavaScript Pattern:**
```javascript
// static/js/organizer/registration_actions.js
document.addEventListener('DOMContentLoaded', () => {
    // Attach event listeners to approve buttons
    document.querySelectorAll('[data-action="approve-registration"]').forEach(button => {
        button.addEventListener('click', async (e) => {
            e.preventDefault();
            
            const registrationId = button.dataset.registrationId;
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            
            try {
                // Call backend endpoint (service handles business logic)
                const response = await fetch(`/tournaments/api/registrations/${registrationId}/approve/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    }
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Update UI
                    button.textContent = '✓ Approved';
                    button.disabled = true;
                    showToast('Registration approved successfully', 'success');
                } else {
                    showToast(data.error || 'Approval failed', 'error');
                }
            } catch (error) {
                console.error('Approval error:', error);
                showToast('Network error. Please try again.', 'error');
            }
        });
    });
});

function showToast(message, type) {
    // Simple toast notification implementation
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}
```

---

### 3.4 HTMX (Optional Enhancement)

**HTMX Use Cases:**
- Auto-refreshing lists (pending registrations, live roster)
- Inline form submissions without full page reload
- Partial template updates (swap specific divs)
- Polling for real-time updates

**HTMX Pattern:**
```django
{# Auto-refreshing roster #}
<div id="roster-list" 
     hx-get="{% url 'tournaments:lobby_roster_partial' tournament.slug %}"
     hx-trigger="every 5s">
    {# Server returns updated HTML #}
    {% include 'tournaments/lobby/_roster_partial.html' %}
</div>

{# Inline approve button #}
<button hx-post="{% url 'tournaments:approve_registration' tournament.id registration.id %}"
        hx-target="#registration-{{ registration.id }}"
        hx-swap="outerHTML"
        class="btn-primary">
    Approve
</button>
```

**Backend Partial View:**
```python
def lobby_roster_partial(request, slug):
    """Return partial HTML for HTMX roster updates."""
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Service handles data aggregation
    roster_data = LobbyService.get_roster(tournament.id)
    
    return render(request, 'tournaments/lobby/_roster_partial.html', {
        'roster_data': roster_data
    })
```

---

## 4. DATA FLOW PATTERNS

### 4.1 Read Operations (Display Data)

**Pattern:** View → ORM → Template

```python
# View performs read-only query
def organizer_dashboard(request, slug):
    tournament = get_object_or_404(
        Tournament.objects.select_related('game', 'organizer'),
        slug=slug
    )
    
    # Aggregate stats (read-only)
    stats = {
        'total_registrations': tournament.registrations.count(),
        'pending_registrations': tournament.registrations.filter(status=Registration.PENDING).count(),
        'checked_in': tournament.registrations.filter(checked_in=True).count(),
    }
    
    return render(request, 'tournaments/organizer/dashboard.html', {
        'tournament': tournament,
        'stats': stats,
    })
```

**Rule:** Read-only ORM queries in views are acceptable. No `.save()` or `.update()`.

---

### 4.2 Write Operations (State Changes)

**Pattern:** View → Service → ORM → Side Effects

```python
# View delegates to service
def approve_registration(request, tournament_id, registration_id):
    registration = get_object_or_404(Registration, id=registration_id)
    
    # Permission check (view responsibility)
    if not OrganizerPermissionChecker.can_manage_registrations(request.user, registration.tournament):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    try:
        # Service handles business logic
        approved_registration = RegistrationService.approve(
            registration=registration,
            approved_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'registration': {
                'id': approved_registration.id,
                'status': approved_registration.status,
                'approved_at': approved_registration.approved_at.isoformat()
            }
        })
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
```

**Service Implementation:**
```python
# Service encapsulates business logic
class RegistrationService:
    @staticmethod
    @transaction.atomic
    def approve(registration: Registration, approved_by: User) -> Registration:
        # Validation
        if registration.status != Registration.PENDING:
            raise ValidationError("Only pending registrations can be approved")
        
        if registration.tournament.status == Tournament.CANCELLED:
            raise ValidationError("Cannot approve registration for cancelled tournament")
        
        # State change
        registration.status = Registration.CONFIRMED
        registration.approved_by = approved_by
        registration.approved_at = timezone.now()
        registration.save()
        
        # Side effects
        EmailService.send_registration_confirmed(registration)
        AuditLog.create(
            action='registration_approved',
            user=approved_by,
            tournament=registration.tournament,
            target_id=registration.id
        )
        
        return registration
```

---

### 4.3 Aggregation Operations (Complex Queries)

**Pattern:** View → Service → ORM Aggregation → Template

**When to Use Service for Reads:**
- Complex joins across multiple models
- Business logic in query (e.g., "active participants" definition)
- Reusable queries across multiple views
- Data transformation or enrichment

**Example:**
```python
# Service handles complex aggregation
class LobbyService:
    @staticmethod
    def get_roster(tournament_id: int) -> dict:
        """Get tournament roster with check-in status."""
        tournament = Tournament.objects.get(id=tournament_id)
        
        registrations = Registration.objects.filter(
            tournament=tournament,
            status=Registration.CONFIRMED,
            is_deleted=False
        ).select_related('user', 'user__userprofile', 'team').order_by(
            '-checked_in', 'created_at'
        )
        
        return {
            'total': registrations.count(),
            'checked_in': registrations.filter(checked_in=True).count(),
            'participants': [
                {
                    'id': reg.id,
                    'name': reg.team.name if reg.team else reg.user.username,
                    'checked_in': reg.checked_in,
                    'checked_in_at': reg.checked_in_at.isoformat() if reg.checked_in_at else None,
                }
                for reg in registrations
            ]
        }

# View delegates to service
def lobby_roster_api(request, slug):
    tournament = get_object_or_404(Tournament, slug=slug)
    roster_data = LobbyService.get_roster(tournament.id)
    return JsonResponse(roster_data)
```

---

## 5. REAL-TIME UPDATES STRATEGY

### 5.1 Polling (Short-Term Solution)

**Use Case:** Auto-refresh roster, pending registrations, match results

**Pattern:**
```django
{# HTMX polling every 10 seconds #}
<div id="roster-container"
     hx-get="{% url 'tournaments:lobby_roster_partial' tournament.slug %}"
     hx-trigger="every 10s"
     hx-swap="innerHTML">
    {% include 'tournaments/lobby/_roster_partial.html' %}
</div>
```

**Pros:**
- Simple to implement
- Works with existing architecture
- No additional infrastructure

**Cons:**
- Increased server load
- Not truly real-time (10s delay)
- Unnecessary requests if no changes

---

### 5.2 WebSockets (Long-Term Solution)

**Use Case:** Live match updates, instant notifications, real-time roster

**Pattern:**
```python
# Django Channels consumer
class LobbyConsumer(WebsocketConsumer):
    def connect(self):
        self.tournament_slug = self.scope['url_route']['kwargs']['slug']
        self.room_group_name = f'lobby_{self.tournament_slug}'
        
        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        self.accept()
    
    def receive(self, text_data):
        # Handle incoming messages
        pass
    
    def roster_update(self, event):
        # Send roster update to WebSocket
        self.send(text_data=json.dumps({
            'type': 'roster_update',
            'data': event['roster_data']
        }))
```

**Service Integration:**
```python
# Service dispatches WebSocket events
class CheckInService:
    @staticmethod
    def check_in(tournament: Tournament, user: User) -> Registration:
        # ... business logic ...
        
        # Dispatch WebSocket event
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'lobby_{tournament.slug}',
            {
                'type': 'roster_update',
                'roster_data': LobbyService.get_roster(tournament.id)
            }
        )
        
        return registration
```

**Pros:**
- True real-time updates
- Efficient (push, not poll)
- Better UX

**Cons:**
- Requires Django Channels + Redis
- More complex infrastructure
- Stateful connections

---

## 6. ERROR HANDLING PATTERNS

### 6.1 Service Layer Errors

**Rule:** Services raise `ValidationError` for business rule violations.

```python
from django.core.exceptions import ValidationError

class RegistrationService:
    @staticmethod
    def approve(registration: Registration, approved_by: User) -> Registration:
        # Business rule validation
        if registration.status != Registration.PENDING:
            raise ValidationError(
                "Only pending registrations can be approved. "
                f"Current status: {registration.get_status_display()}"
            )
        
        if not registration.payment or registration.payment.status != Payment.VERIFIED:
            raise ValidationError("Cannot approve registration without verified payment")
        
        # ... proceed with approval ...
```

---

### 6.2 View Layer Error Handling

**Rule:** Views catch service errors and return appropriate HTTP responses.

```python
def approve_registration(request, tournament_id, registration_id):
    registration = get_object_or_404(Registration, id=registration_id)
    
    try:
        # Delegate to service
        approved_registration = RegistrationService.approve(
            registration=registration,
            approved_by=request.user
        )
        
        return JsonResponse({'success': True})
        
    except ValidationError as e:
        # Business rule violation - 400 Bad Request
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
        
    except PermissionDenied as e:
        # Authorization failure - 403 Forbidden
        return JsonResponse({
            'success': False,
            'error': 'You do not have permission to perform this action'
        }, status=403)
        
    except Exception as e:
        # Unexpected error - 500 Internal Server Error
        logger.exception(f"Unexpected error approving registration {registration_id}")
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred. Please try again.'
        }, status=500)
```

---

### 6.3 Frontend Error Display

**Rule:** JavaScript displays user-friendly error messages from backend.

```javascript
async function approveRegistration(registrationId) {
    try {
        const response = await fetch(`/api/registrations/${registrationId}/approve/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showToast('Registration approved successfully', 'success');
            refreshRegistrationList();
        } else {
            // Display error message from backend
            showToast(data.error || 'Approval failed', 'error');
        }
    } catch (error) {
        // Network error
        showToast('Network error. Please check your connection.', 'error');
        console.error('Approval error:', error);
    }
}
```

---

## 7. TESTING STRATEGY

### 7.1 Service Layer Tests (Priority 1)

**Rule:** All service methods MUST have unit tests covering:
- Happy path
- Business rule violations (ValidationError cases)
- Edge cases
- Side effects (emails, audit logs, webhooks)

**Example:**
```python
# tests/services/test_registration_service.py
class RegistrationServiceTest(TestCase):
    def test_approve_pending_registration_success(self):
        """Approve a pending registration with verified payment."""
        registration = RegistrationFactory(
            status=Registration.PENDING,
            payment__status=Payment.VERIFIED
        )
        
        approved = RegistrationService.approve(
            registration=registration,
            approved_by=self.organizer_user
        )
        
        self.assertEqual(approved.status, Registration.CONFIRMED)
        self.assertEqual(approved.approved_by, self.organizer_user)
        self.assertIsNotNone(approved.approved_at)
        
        # Verify side effects
        self.assertEqual(len(mail.outbox), 1)  # Email sent
        self.assertTrue(AuditLog.objects.filter(
            action='registration_approved',
            target_id=registration.id
        ).exists())
    
    def test_approve_non_pending_registration_fails(self):
        """Cannot approve already confirmed registration."""
        registration = RegistrationFactory(status=Registration.CONFIRMED)
        
        with self.assertRaises(ValidationError) as cm:
            RegistrationService.approve(
                registration=registration,
                approved_by=self.organizer_user
            )
        
        self.assertIn('Only pending registrations can be approved', str(cm.exception))
```

---

### 7.2 View Layer Tests (Priority 2)

**Rule:** Test views as thin controllers - verify they call services correctly.

```python
# tests/views/test_organizer_views.py
class ApproveRegistrationViewTest(TestCase):
    def test_approve_registration_calls_service(self, mock_service):
        """View delegates to RegistrationService.approve()."""
        registration = RegistrationFactory()
        
        self.client.login(username='organizer', password='password')
        response = self.client.post(
            reverse('tournaments:approve_registration', args=[registration.tournament.id, registration.id])
        )
        
        self.assertEqual(response.status_code, 200)
        mock_service.approve.assert_called_once_with(
            registration=registration,
            approved_by=self.user
        )
    
    def test_approve_registration_handles_validation_error(self, mock_service):
        """View returns 400 when service raises ValidationError."""
        mock_service.approve.side_effect = ValidationError("Invalid status")
        
        response = self.client.post(...)
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], "Invalid status")
```

---

### 7.3 Integration Tests (Priority 3)

**Rule:** Test complete user flows end-to-end.

```python
class RegistrationApprovalFlowTest(TestCase):
    def test_organizer_approves_registration_end_to_end(self):
        """Complete flow: organizer approves → participant receives email → status updated."""
        tournament = TournamentFactory()
        registration = RegistrationFactory(tournament=tournament, status=Registration.PENDING)
        organizer = UserFactory()
        
        self.client.login(username=organizer.username, password='password')
        
        # Submit approval
        response = self.client.post(
            reverse('tournaments:approve_registration', args=[tournament.id, registration.id])
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        
        # Verify database
        registration.refresh_from_db()
        self.assertEqual(registration.status, Registration.CONFIRMED)
        self.assertEqual(registration.approved_by, organizer)
        
        # Verify email sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('approved', mail.outbox[0].subject.lower())
        
        # Verify audit log
        self.assertTrue(AuditLog.objects.filter(
            action='registration_approved',
            user=organizer,
            target_id=registration.id
        ).exists())
```

---

## 8. MIGRATION STRATEGY

### 8.1 Refactoring Organizer Views

**Current State:** Direct ORM manipulation in 20+ functions

**Target State:** All functions delegate to services

**Migration Steps per Function:**
1. Identify existing ORM mutation code
2. Create/enhance service method with equivalent logic + side effects
3. Add service unit tests
4. Refactor view to call service
5. Add view integration test
6. Verify in staging
7. Deploy

**Example Migration:**

**BEFORE:**
```python
# apps/tournaments/views/organizer.py
def approve_registration(request, tournament_id, registration_id):
    registration = get_object_or_404(Registration, id=registration_id)
    registration.status = 'confirmed'
    registration.save()
    return JsonResponse({'success': True})
```

**AFTER:**
```python
# apps/tournaments/views/organizer.py
from apps.tournaments.services.registration_service import RegistrationService

def approve_registration(request, tournament_id, registration_id):
    registration = get_object_or_404(Registration, id=registration_id)
    
    try:
        approved = RegistrationService.approve(
            registration=registration,
            approved_by=request.user
        )
        return JsonResponse({'success': True})
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
```

**SERVICE ADDED:**
```python
# apps/tournaments/services/registration_service.py
class RegistrationService:
    @staticmethod
    @transaction.atomic
    def approve(registration: Registration, approved_by: User) -> Registration:
        # Validation
        if registration.status != Registration.PENDING:
            raise ValidationError("Only pending registrations can be approved")
        
        # State change
        registration.status = Registration.CONFIRMED
        registration.approved_by = approved_by
        registration.approved_at = timezone.now()
        registration.save()
        
        # Side effects
        EmailService.send_registration_confirmed(registration)
        AuditLog.create(action='registration_approved', user=approved_by, target=registration)
        
        return registration
```

---

### 8.2 Completing Incomplete Implementations

**Current State:** TODO comments in result_submission.py, organizer_results.py

**Target State:** Complete implementations with service calls

**Priority Functions:**
1. `confirm_match_result()` - organizer_results.py
2. `reject_match_result()` - organizer_results.py
3. `override_match_result()` - organizer_results.py
4. `report_dispute()` - result_submission.py
5. `submit_result()` - result_submission.py

**Implementation Pattern:**
1. Create MatchService methods (if not exist)
2. Create DisputeService methods (if not exist)
3. Implement view functions to call services
4. Remove TODO comments
5. Add tests
6. Deploy

---

## 9. ENFORCEMENT MECHANISMS

### 9.1 Code Review Checklist

**Required for all PRs touching tournament views:**
- [ ] No `.save()` calls in view functions
- [ ] No `.update()` calls in view functions
- [ ] All state changes delegate to service methods
- [ ] Service methods have unit tests
- [ ] ValidationError properly handled in views
- [ ] Side effects (emails, logs) implemented in services
- [ ] No direct tournament_ops imports in views

---

### 9.2 Linting Rules (Optional)

**Custom pylint rule to detect ORM mutations in views:**
```python
# .pylintrc
[MESSAGES CONTROL]
enable=no-model-save-in-views

# Custom checker (hypothetical)
# Flags: model_instance.save() in files matching **/views/*.py
```

---

### 9.3 Architecture Decision Record (ADR)

**ADR-001: Service Layer for All State Changes**

**Status:** Accepted  
**Date:** December 19, 2025

**Context:**
- Current organizer views bypass service layer
- Missing notifications, audit logs, validation
- tournament_ops integration unreachable from views

**Decision:**
- ALL tournament state changes MUST go through service methods
- Views act as thin controllers (orchestration only)
- Services encapsulate business logic, validations, side effects

**Consequences:**
- Positive: Testable, maintainable, consistent
- Positive: Enables tournament_ops integration
- Positive: Centralized business logic
- Negative: Requires refactoring existing views
- Negative: Steeper learning curve for new developers

**Compliance:**
- Enforced via code review
- Checked in PR templates
- Documented in developer onboarding

---

## 10. SUMMARY

**Architecture Pillars:**

1. **Django Templates + Tailwind + Vanilla JS** - No React, no build step, server-rendered
2. **Thin Controllers** - Views orchestrate, don't implement
3. **Service Layer** - All business logic, validations, side effects
4. **tournament_ops via Services** - Never direct calls from views
5. **Read Operations** - Direct ORM acceptable for read-only queries
6. **Write Operations** - MUST go through services
7. **Error Handling** - Services raise ValidationError, views catch and format
8. **Testing** - Service tests first, view tests second, integration tests third
9. **Real-Time** - HTMX polling (Phase 1), WebSockets (Phase 2+)
10. **Enforcement** - Code review, testing, documentation

**Reference Implementations:**
- ✅ `apps/tournaments/views/checkin.py` - Gold standard for service usage
- ✅ `apps/tournaments/views/lobby.py` - Gold standard for service usage
- ❌ `apps/tournaments/views/organizer.py` - Needs refactoring (anti-pattern)

---

**End of Target Architecture**
