# PART 5.2: Backend Integration, Testing & Deployment

**Navigation:**
- [← Previous: PART_5.1 - Implementation Roadmap & Sprint Planning](./PART_5.1_IMPLEMENTATION_ROADMAP_SPRINT_PLANNING.md)
- [↑ Back to Index](./INDEX_MASTER_NAVIGATION.md)

---

## Table of Contents (Part 5.2)

### Section 4: Backend Integration Points (Continuation)
- 4.1 Django Views Architecture - Example 1: Tournament Listing (Template + HTMX)
- 4.1 Django Views Architecture - Example 2: Tournament Detail (Full Page + API)
- 4.2 API Endpoint Mapping
- 4.3 WebSocket Channel Configuration
- 4.4 Database Query Optimization
- 4.5 Background Tasks with Celery
- 4.6 Model-View-Template Flow Examples

### Section 5: Testing & QA Strategy
- 5.1 Testing Pyramid
- 5.2 Backend Testing
- 5.3 Frontend Testing
- 5.4 End-to-End Tests (Cypress)
- 5.5 Accessibility Testing
- 5.6 Performance Testing
- 5.7 Test Coverage Requirements

### Section 6: Deployment & DevOps
- 6.1 CI/CD Pipeline (GitHub Actions)
- 6.2 Docker Configuration
- 6.3 Deployment Script (Blue-Green)
- 6.4 Monitoring & Logging

### Section 7: Team Structure & Responsibilities
- 7.1 Development Roles
- 7.2 Communication Channels
- 7.3 Development Workflow

### Section 8: Integration Checklist & Dependencies
- 8.1 Part 2 (Architecture) Integration
- 8.2 Part 3 (Database) Integration
- 8.3 Part 4 (UI/UX) Integration

### Section 9: Post-Launch & Iteration Plan
- 9.1 Monitoring Metrics
- 9.2 User Feedback Collection
- 9.3 Feature Iteration Roadmap
- 9.4 Maintenance Schedule
- 9.5 Scaling Plan

### Section 10: Appendix: Technical Reference
- 10.1 Key Dependencies
- 10.2 Environment Variables
- 10.3 Useful Commands

### Conclusion

---

## 4. Backend Integration Points (Continuation)

### 4.1 Django Views Architecture (Continued)

**Example 1: Tournament Listing (Template + HTMX)**

```python
# apps/tournaments/views.py
from django.views.generic import ListView
from django.db.models import Q, Count
from .models import Tournament

class TournamentListView(ListView):
    model = Tournament
    template_name = 'tournaments/list.html'
    context_object_name = 'tournaments'
    paginate_by = 12
    
    def get_queryset(self):
        qs = Tournament.objects.filter(
            status__in=['PUBLISHED', 'REGISTRATION_OPEN', 'ONGOING']
        ).select_related(
            'organizer', 'game'
        ).prefetch_related(
            'registrations'
        ).annotate(
            registration_count=Count('registrations')
        )
        
        # Apply filters
        game = self.request.GET.get('game')
        if game:
            qs = qs.filter(game__slug=game)
        
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        
        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search)
            )
        
        return qs.order_by('-start_date')
    
    def get_template_names(self):
        # HTMX request returns partial
        if self.request.htmx:
            return ['partials/tournament_grid.html']
        return ['tournaments/list.html']
```

**Example 2: Tournament Detail (Full Page + API)**

```python
from django.views.generic import DetailView
from rest_framework.generics import RetrieveAPIView
from .serializers import TournamentDetailSerializer

class TournamentDetailView(DetailView):
    model = Tournament
    template_name = 'tournaments/detail.html'
    context_object_name = 'tournament'
    
    def get_queryset(self):
        return Tournament.objects.select_related(
            'organizer__user',
            'game',
        ).prefetch_related(
            'registrations__team',
            'custom_fields',
            'sponsors'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.object
        
        # Check if user already registered
        if self.request.user.is_authenticated:
            context['user_registration'] = tournament.registrations.filter(
                team__members__user=self.request.user
            ).first()
        
        # Calculate spots remaining
        context['spots_remaining'] = (
            tournament.max_teams - tournament.registrations.count()
        )
        
        # Get upcoming matches
        context['upcoming_matches'] = tournament.matches.filter(
            status='SCHEDULED'
        ).select_related('team_a', 'team_b')[:5]
        
        return context

# API version for mobile/SPA
class TournamentDetailAPIView(RetrieveAPIView):
    queryset = Tournament.objects.all()
    serializer_class = TournamentDetailSerializer
    lookup_field = 'slug'
```

### 4.2 API Endpoint Mapping

**REST API Structure:**

```
/api/v1/
├── tournaments/
│   ├── GET    /                      # List tournaments (filtered)
│   ├── POST   /                      # Create tournament (organizer only)
│   ├── GET    /{slug}/               # Tournament detail
│   ├── PATCH  /{slug}/               # Update tournament (organizer only)
│   ├── DELETE /{slug}/               # Delete tournament (organizer only)
│   ├── POST   /{slug}/register/      # Submit registration
│   ├── GET    /{slug}/bracket/       # Get bracket data
│   └── GET    /{slug}/matches/       # List matches
├── registrations/
│   ├── GET    /                      # User's registrations
│   ├── GET    /{id}/                 # Registration detail
│   ├── POST   /{id}/payment/         # Submit payment proof
│   └── DELETE /{id}/                 # Withdraw registration
├── matches/
│   ├── GET    /{id}/                 # Match detail
│   ├── POST   /{id}/submit_result/   # Submit result
│   ├── POST   /{id}/dispute/         # Dispute result
│   └── POST   /{id}/predict/         # Submit prediction (spectator)
├── payments/
│   ├── GET    /                      # Admin: Pending payments
│   ├── POST   /{id}/approve/         # Admin: Approve payment
│   └── POST   /{id}/reject/          # Admin: Reject payment
├── certificates/
│   ├── GET    /{id}/                 # View certificate
│   ├── GET    /{id}/download/        # Download PDF
│   └── GET    /{id}/verify/          # Verify certificate
└── users/
    ├── GET    /profile/              # User profile
    ├── PATCH  /profile/              # Update profile
    └── GET    /stats/                # User statistics
```

**API Authentication:**

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}
```

**Example API View with Permissions:**

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Tournament, Registration
from .serializers import RegistrationSerializer
from .permissions import IsOrganizerOrReadOnly

class RegistrationViewSet(viewsets.ModelViewSet):
    serializer_class = RegistrationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Users see only their registrations
        if self.request.user.is_staff:
            return Registration.objects.all()
        return Registration.objects.filter(
            team__members__user=self.request.user
        )
    
    def create(self, request, *args, **kwargs):
        """Submit tournament registration"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Validate tournament capacity
        tournament = serializer.validated_data['tournament']
        if tournament.registrations.count() >= tournament.max_teams:
            return Response(
                {'error': 'Tournament is full'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate registration window
        if tournament.status != 'REGISTRATION_OPEN':
            return Response(
                {'error': 'Registration is not open'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def submit_payment(self, request, pk=None):
        """Upload payment proof"""
        registration = self.get_object()
        
        # Validate user owns this registration
        if not registration.team.members.filter(user=request.user).exists():
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        payment_proof = request.FILES.get('payment_proof')
        if not payment_proof:
            return Response(
                {'error': 'Payment proof required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        registration.payment_proof = payment_proof
        registration.payment_status = 'PENDING_VERIFICATION'
        registration.save()
        
        # Send notification to admins
        from .tasks import notify_payment_submitted
        notify_payment_submitted.delay(registration.id)
        
        return Response({'message': 'Payment submitted successfully'})
```

### 4.3 WebSocket Channel Configuration

**Django Channels Setup:**

```python
# settings.py
INSTALLED_APPS = [
    'daphne',  # Must be before django.contrib.staticfiles
    'django.contrib.staticfiles',
    'channels',
    # ...
]

ASGI_APPLICATION = 'deltacrown.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('redis', 6379)],
            'capacity': 1500,
            'expiry': 10,
        },
    },
}

# asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from apps.tournaments import routing as tournament_routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(
            tournament_routing.websocket_urlpatterns
        )
    ),
})
```

**WebSocket Consumer Example:**

```python
# apps/tournaments/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Tournament, Match

class TournamentLiveConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.tournament_id = self.scope['url_route']['kwargs']['tournament_id']
        self.room_group_name = f'tournament_{self.tournament_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        
        # Send initial data
        tournament_data = await self.get_tournament_data()
        await self.send(text_data=json.dumps({
            'type': 'initial_data',
            'tournament': tournament_data
        }))
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.dumps(text_data)
        message_type = data.get('type')
        
        if message_type == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
        
        elif message_type == 'chat_message':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': data['message'],
                    'username': self.scope['user'].username
                }
            )
    
    # Handler for match_update messages
    async def match_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'match_update',
            'match_id': event['match_id'],
            'score': event['score']
        }))
    
    # Handler for chat messages
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'live_chat',
            'message': {
                'username': event['username'],
                'text': event['message']
            }
        }))
    
    @database_sync_to_async
    def get_tournament_data(self):
        tournament = Tournament.objects.get(id=self.tournament_id)
        return {
            'id': tournament.id,
            'title': tournament.title,
            'status': tournament.status,
            'registration_count': tournament.registrations.count()
        }

# Broadcasting match updates from views
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def broadcast_match_update(match):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'tournament_{match.tournament_id}',
        {
            'type': 'match_update',
            'match_id': match.id,
            'score': {
                'team_a': match.score_team_a,
                'team_b': match.score_team_b
            }
        }
    )
```

**URL Routing:**

```python
# apps/tournaments/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(
        r'ws/tournament/(?P<tournament_id>\d+)/$',
        consumers.TournamentLiveConsumer.as_asgi()
    ),
]
```

### 4.4 Database Query Optimization

**Common Optimization Patterns:**

```python
# ❌ Bad: N+1 query problem
tournaments = Tournament.objects.all()
for tournament in tournaments:
    print(tournament.organizer.username)  # Extra query per tournament
    print(tournament.registrations.count())  # Extra query per tournament

# ✅ Good: Use select_related and prefetch_related
tournaments = Tournament.objects.select_related(
    'organizer',  # ForeignKey
    'game'
).prefetch_related(
    'registrations',  # ManyToMany or reverse ForeignKey
    'sponsors'
).annotate(
    registration_count=Count('registrations')
)

# ✅ Good: Prefetch with custom queryset
from django.db.models import Prefetch

tournaments = Tournament.objects.prefetch_related(
    Prefetch(
        'registrations',
        queryset=Registration.objects.filter(
            payment_status='APPROVED'
        ).select_related('team')
    )
)

# ✅ Good: Use only() and defer() for large models
tournaments = Tournament.objects.only(
    'id', 'title', 'start_date', 'status'
)  # Only fetch these fields

# ✅ Good: Database indexes (in models)
class Tournament(models.Model):
    title = models.CharField(max_length=200, db_index=True)
    status = models.CharField(max_length=20, db_index=True)
    start_date = models.DateTimeField(db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'start_date']),  # Composite index
            models.Index(fields=['-created_at']),  # Descending order
        ]
```

**Caching Strategy:**

```python
from django.core.cache import cache
from django.views.decorators.cache import cache_page

# Cache entire view response (5 minutes)
@cache_page(60 * 5)
def tournament_list(request):
    # ...
    pass

# Cache specific queryset
def get_featured_tournaments():
    cache_key = 'featured_tournaments'
    tournaments = cache.get(cache_key)
    
    if tournaments is None:
        tournaments = Tournament.objects.filter(
            is_featured=True,
            status='REGISTRATION_OPEN'
        ).select_related('organizer', 'game')[:6]
        
        cache.set(cache_key, tournaments, 60 * 10)  # 10 minutes
    
    return tournaments

# Invalidate cache on update
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Tournament)
def invalidate_tournament_cache(sender, instance, **kwargs):
    cache.delete('featured_tournaments')
    cache.delete(f'tournament_{instance.id}')
```

### 4.5 Background Tasks with Celery

**Celery Setup:**

```python
# deltacrown/celery.py
from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')

app = Celery('deltacrown')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# settings.py
CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Dhaka'
```

**Example Background Tasks:**

```python
# apps/tournaments/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from .models import Tournament, Registration, Certificate
from .utils import generate_certificate_pdf

@shared_task
def send_payment_approval_email(registration_id):
    """Send email when payment approved"""
    registration = Registration.objects.select_related(
        'team', 'tournament'
    ).get(id=registration_id)
    
    send_mail(
        subject=f'Payment Approved - {registration.tournament.title}',
        message=f'Your payment has been approved. You are now registered!',
        from_email='noreply@deltacrown.com',
        recipient_list=[registration.team.captain.email],
        fail_silently=False,
    )

@shared_task
def generate_certificates_for_tournament(tournament_id):
    """Generate certificates for all winners (runs after tournament ends)"""
    tournament = Tournament.objects.get(id=tournament_id)
    
    # Get top 3 teams
    winners = tournament.get_winners()  # Custom method
    
    for rank, team in enumerate(winners, start=1):
        for player in team.members.all():
            certificate = Certificate.objects.create(
                tournament=tournament,
                player=player.user,
                rank=rank,
                verification_code=Certificate.generate_code()
            )
            
            # Generate PDF
            pdf_data = generate_certificate_pdf(certificate)
            certificate.pdf_file.save(
                f'cert_{certificate.id}.pdf',
                pdf_data
            )
    
    return f'Generated {len(winners)} certificates'

@shared_task
def check_tournament_start_times():
    """Cron job: Check for tournaments that should start (runs every minute)"""
    from django.utils import timezone
    now = timezone.now()
    
    tournaments = Tournament.objects.filter(
        status='REGISTRATION_OPEN',
        start_time__lte=now
    )
    
    for tournament in tournaments:
        tournament.status = 'ONGOING'
        tournament.save()
        
        # Generate brackets
        from .bracket_generator import generate_bracket
        generate_bracket(tournament)
        
        # Notify participants
        notify_tournament_started.delay(tournament.id)
    
    return f'Started {tournaments.count()} tournaments'

# Celery Beat schedule (periodic tasks)
from celery.schedules import crontab

app.conf.beat_schedule = {
    'check-tournament-starts': {
        'task': 'apps.tournaments.tasks.check_tournament_start_times',
        'schedule': crontab(minute='*/1'),  # Every minute
    },
    'send-check-in-reminders': {
        'task': 'apps.tournaments.tasks.send_check_in_reminders',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
}
```

### 4.6 Model-View-Template Flow Examples

**Example: Registration Submission Flow**

```
1. User clicks "Register Now" button
   └─> Frontend: HTMX POST request
       └─> Backend: RegistrationViewSet.create()
           ├─> Validate tournament capacity
           ├─> Validate registration window
           ├─> Create Registration instance
           ├─> Trigger Celery task: send_confirmation_email.delay()
           └─> Return: JSON response or HTML partial
               └─> Frontend: Display confirmation modal + analytics tracking

2. User uploads payment proof
   └─> Frontend: File upload with progress bar
       └─> Backend: RegistrationViewSet.submit_payment()
           ├─> Upload file to S3 / local storage
           ├─> Update payment_status = 'PENDING_VERIFICATION'
           ├─> Trigger Celery task: notify_admin_payment.delay()
           └─> Return: Success message
               └─> Frontend: Show "Payment submitted" confirmation

3. Admin reviews payment
   └─> Frontend: Admin panel click "Approve"
       └─> Backend: PaymentViewSet.approve()
           ├─> Update payment_status = 'APPROVED'
           ├─> Increment registration count
           ├─> Trigger Celery task: send_approval_email.delay()
           ├─> Broadcast WebSocket: registration_update
           └─> Return: Updated payment status
               └─> Frontend: Badge changes to green "Approved"
```

**Database Transaction Example:**

```python
from django.db import transaction

@transaction.atomic
def submit_match_result(match_id, score_team_a, score_team_b, submitted_by):
    """Atomic transaction for match result submission"""
    match = Match.objects.select_for_update().get(id=match_id)
    
    # Validate match state
    if match.status != 'IN_PROGRESS':
        raise ValueError('Match is not in progress')
    
    # Update match
    match.score_team_a = score_team_a
    match.score_team_b = score_team_b
    match.result_submitted_by = submitted_by
    match.status = 'AWAITING_CONFIRMATION'
    match.save()
    
    # Determine winner
    if score_team_a > score_team_b:
        winner = match.team_a
    elif score_team_b > score_team_a:
        winner = match.team_b
    else:
        raise ValueError('Scores cannot be equal')
    
    # Create match history entry
    MatchHistory.objects.create(
        match=match,
        action='RESULT_SUBMITTED',
        data={'score_a': score_team_a, 'score_b': score_team_b},
        user=submitted_by
    )
    
    # Update bracket (if opponent confirms)
    if match.result_confirmed:
        next_match = match.bracket.get_next_match(match)
        if next_match:
            next_match.assign_team(winner)
            next_match.save()
    
    return match
```

---

## 5. Testing & QA Strategy

### 5.1 Testing Pyramid

```
           /\
          /E2E\         10% - End-to-End (Cypress)
         /______\
        /  API   \       20% - Integration (pytest-django)
       /__________\
      /   Unit     \     70% - Unit Tests (pytest, Jest)
     /______________\
```

**Test Coverage Targets:**
- Backend: >80% coverage
- Frontend: >70% coverage
- Critical paths: 100% coverage (payment, registration, bracket)

### 5.2 Backend Testing

**Unit Tests (pytest + pytest-django):**

```python
# tests/test_tournament_registration.py
import pytest
from apps.tournaments.models import Tournament, Registration
from apps.teams.models import Team

@pytest.mark.django_db
class TestTournamentRegistration:
    
    def test_registration_success(self, tournament, team):
        """Test successful tournament registration"""
        registration = Registration.objects.create(
            tournament=tournament,
            team=team,
            payment_status='PENDING'
        )
        assert registration.id is not None
        assert registration.tournament == tournament
        assert registration.payment_status == 'PENDING'
    
    def test_registration_capacity_limit(self, tournament_full, team):
        """Test registration rejected when tournament full"""
        with pytest.raises(ValidationError):
            tournament_full.register_team(team)
    
    def test_payment_approval_flow(self, registration):
        """Test payment approval updates status"""
        registration.approve_payment()
        registration.refresh_from_db()
        
        assert registration.payment_status == 'APPROVED'
        assert registration.approved_at is not None

# conftest.py (fixtures)
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def user():
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )

@pytest.fixture
def tournament():
    from apps.tournaments.models import Tournament
    return Tournament.objects.create(
        title='Test Tournament',
        max_teams=16,
        status='REGISTRATION_OPEN'
    )

@pytest.fixture
def team(user):
    from apps.teams.models import Team
    return Team.objects.create(
        name='Test Team',
        captain=user
    )
```

**API Tests:**

```python
# tests/test_api_tournaments.py
import pytest
from rest_framework.test import APIClient
from rest_framework import status

@pytest.mark.django_db
class TestTournamentAPI:
    
    def setup_method(self):
        self.client = APIClient()
    
    def test_list_tournaments(self, tournament):
        """Test GET /api/v1/tournaments/"""
        response = self.client.get('/api/v1/tournaments/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) > 0
    
    def test_create_tournament_requires_auth(self):
        """Test POST /api/v1/tournaments/ requires authentication"""
        response = self.client.post('/api/v1/tournaments/', {})
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_register_team(self, user, tournament, team):
        """Test POST /api/v1/tournaments/{id}/register/"""
        self.client.force_authenticate(user=user)
        
        response = self.client.post(
            f'/api/v1/tournaments/{tournament.id}/register/',
            {'team_id': team.id}
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert tournament.registrations.count() == 1
```

### 5.3 Frontend Testing

**Component Tests (Jest + Testing Library):**

```javascript
// __tests__/components/Button.test.js
import { render, screen, fireEvent } from '@testing-library/dom';
import { Button } from '@/components/Button';

describe('Button Component', () => {
    test('renders with text', () => {
        render(Button({ text: 'Click Me' }));
        expect(screen.getByText('Click Me')).toBeInTheDocument();
    });
    
    test('calls onClick handler', () => {
        const handleClick = jest.fn();
        render(Button({ text: 'Click Me', onClick: handleClick }));
        
        fireEvent.click(screen.getByText('Click Me'));
        expect(handleClick).toHaveBeenCalledTimes(1);
    });
    
    test('applies variant classes', () => {
        const { container } = render(Button({ variant: 'primary' }));
        expect(container.firstChild).toHaveClass('btn-primary');
    });
});
```

### 5.4 End-to-End Tests (Cypress)

```javascript
// cypress/e2e/tournament_registration.cy.js
describe('Tournament Registration Flow', () => {
    beforeEach(() => {
        cy.login('testuser@example.com', 'password123');
    });
    
    it('completes full registration flow', () => {
        // Navigate to tournament
        cy.visit('/tournaments');
        cy.contains('Test Tournament').click();
        
        // Click register button
        cy.get('[data-analytics-id="dc-btn-register"]').click();
        
        // Fill registration form
        cy.get('#team-name').type('Team Alpha');
        cy.get('#player1-ign').type('Player1');
        cy.get('#player1-phone').type('01700000000');
        
        // Submit registration
        cy.get('[data-analytics-id="dc-btn-submit-registration"]').click();
        
        // Verify confirmation
        cy.contains('Registration Successful').should('be.visible');
        
        // Upload payment proof
        cy.get('[data-analytics-id="dc-input-payment-proof"]')
            .attachFile('payment_proof.png');
        
        cy.get('[data-analytics-id="dc-btn-submit-payment"]').click();
        
        // Verify success message
        cy.contains('Payment submitted').should('be.visible');
    });
});
```

### 5.5 Accessibility Testing

**axe-core Integration:**

```javascript
// cypress/e2e/accessibility.cy.js
describe('Accessibility Tests', () => {
    it('tournament listing page has no violations', () => {
        cy.visit('/tournaments');
        cy.injectAxe();
        cy.checkA11y();
    });
    
    it('registration form has no violations', () => {
        cy.visit('/tournaments/test-tournament');
        cy.get('[data-analytics-id="dc-btn-register"]').click();
        cy.injectAxe();
        cy.checkA11y();
    });
});
```

### 5.6 Performance Testing

**Lighthouse CI Configuration:**

```javascript
// lighthouserc.js
module.exports = {
    ci: {
        collect: {
            url: [
                'http://localhost:8000/',
                'http://localhost:8000/tournaments/',
                'http://localhost:8000/tournaments/test-tournament/'
            ],
            numberOfRuns: 3,
        },
        assert: {
            assertions: {
                'categories:performance': ['error', { minScore: 0.9 }],
                'categories:accessibility': ['error', { minScore: 1.0 }],
                'first-contentful-paint': ['error', { maxNumericValue: 2000 }],
                'largest-contentful-paint': ['error', { maxNumericValue: 2500 }],
                'cumulative-layout-shift': ['error', { maxNumericValue: 0.1 }],
            },
        },
    },
};
```

### 5.7 Test Coverage Requirements

| Component | Unit | Integration | E2E | Accessibility |
|-----------|------|-------------|-----|---------------|
| **Auth System** | ✅ 90% | ✅ Yes | ✅ Login flow | ✅ Forms |
| **Tournament CRUD** | ✅ 85% | ✅ Yes | ✅ Full flow | ✅ All pages |
| **Registration** | ✅ 100% | ✅ Yes | ✅ Full flow | ✅ Forms |
| **Payment** | ✅ 100% | ✅ Yes | ✅ Upload flow | ✅ Admin panel |
| **Bracket** | ✅ 90% | ✅ Yes | ✅ Display | ✅ Navigation |
| **Match Results** | ✅ 85% | ✅ Yes | ✅ Submission | ✅ Forms |
| **WebSocket** | ✅ 70% | ✅ Yes | ✅ Live updates | N/A |
| **Certificates** | ✅ 80% | ✅ Yes | ✅ Download | ✅ View page |

---

## 6. Deployment & DevOps

### 6.1 CI/CD Pipeline (GitHub Actions)

**.github/workflows/ci.yml:**

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-django pytest-cov
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
          REDIS_URL: redis://localhost:6379/0
        run: |
          pytest --cov=apps --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
  
  frontend-build:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run linter
        run: npm run lint
      
      - name: Build assets
        run: npm run build
      
      - name: Run Lighthouse CI
        run: |
          npm install -g @lhci/cli
          lhci autorun
  
  deploy-staging:
    needs: [test, frontend-build]
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    
    steps:
      - name: Deploy to staging
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.STAGING_SSH_KEY }}
          script: |
            cd /var/www/deltacrown-staging
            git pull origin develop
            docker-compose up -d --build
            docker-compose exec web python manage.py migrate
            docker-compose exec web python manage.py collectstatic --noinput
  
  deploy-production:
    needs: [test, frontend-build]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    
    steps:
      - name: Deploy to production (blue-green)
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.PROD_SSH_KEY }}
          script: |
            cd /var/www/deltacrown
            ./deploy.sh
```

### 6.2 Docker Configuration

**docker-compose.yml:**

```yaml
version: '3.9'

services:
  web:
    build: .
    command: gunicorn deltacrown.wsgi:application --bind 0.0.0.0:8000 --workers 4
    volumes:
      - .:/app
      - static_volume:/app/static
      - media_volume:/app/media
    env_file:
      - .env
    depends_on:
      - db
      - redis
    networks:
      - app-network
  
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    env_file:
      - .env
    networks:
      - app-network
  
  redis:
    image: redis:7
    networks:
      - app-network
  
  celery:
    build: .
    command: celery -A deltacrown worker -l info
    volumes:
      - .:/app
    env_file:
      - .env
    depends_on:
      - db
      - redis
    networks:
      - app-network
  
  celery-beat:
    build: .
    command: celery -A deltacrown beat -l info
    volumes:
      - .:/app
    env_file:
      - .env
    depends_on:
      - redis
    networks:
      - app-network
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - static_volume:/app/static
      - media_volume:/app/media
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    depends_on:
      - web
    networks:
      - app-network

volumes:
  postgres_data:
  static_volume:
  media_volume:

networks:
  app-network:
    driver: bridge
```

### 6.3 Deployment Script (Blue-Green)

**deploy.sh:**

```bash
#!/bin/bash
set -e

# Configuration
APP_DIR="/var/www/deltacrown"
BLUE_PORT=8000
GREEN_PORT=8001
NGINX_CONF="/etc/nginx/sites-enabled/deltacrown"

# Determine current active environment
CURRENT=$(grep -oP 'proxy_pass.*:\K\d+' $NGINX_CONF)

if [ "$CURRENT" == "$BLUE_PORT" ]; then
    NEW_PORT=$GREEN_PORT
    NEW_ENV="green"
    OLD_ENV="blue"
else
    NEW_PORT=$BLUE_PORT
    NEW_ENV="blue"
    OLD_ENV="red"
fi

echo "Current: $OLD_ENV ($CURRENT) -> Deploying: $NEW_ENV ($NEW_PORT)"

# Pull latest code
cd $APP_DIR
git pull origin main

# Build new environment
docker-compose -f docker-compose.$NEW_ENV.yml up -d --build

# Wait for health check
echo "Waiting for $NEW_ENV environment to be healthy..."
for i in {1..30}; do
    if curl -f http://localhost:$NEW_PORT/healthz/; then
        echo "$NEW_ENV is healthy!"
        break
    fi
    if [ $i == 30 ]; then
        echo "$NEW_ENV failed to start!"
        exit 1
    fi
    sleep 2
done

# Switch nginx to new environment
sed -i "s/:$CURRENT/:$NEW_PORT/" $NGINX_CONF
sudo nginx -t && sudo nginx -s reload

echo "Traffic switched to $NEW_ENV"

# Wait 30 seconds for connections to drain
sleep 30

# Stop old environment
docker-compose -f docker-compose.$OLD_ENV.yml down

echo "Deployment complete! $NEW_ENV is now serving traffic."
```

### 6.4 Monitoring & Logging

**Sentry Configuration:**

```python
# settings.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=os.environ.get('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=True,
    environment=os.environ.get('ENVIRONMENT', 'development'),
)
```

**Prometheus Metrics:**

```python
# apps/core/middleware.py
from prometheus_client import Counter, Histogram
import time

request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')

class MetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - start_time
        
        request_count.labels(request.method, request.path).inc()
        request_duration.observe(duration)
        
        return response
```

---

## 7. Team Structure & Responsibilities

### 7.1 Development Roles

| Role | Team Member | Responsibilities | Key Deliverables |
|------|-------------|------------------|------------------|
| **Frontend Lead** | Dev 1 | Component library, HTMX integration | Tailwind setup, core components |
| **Frontend Dev** | Dev 2 | Page implementations, animations | Tournament screens, player dashboard |
| **Backend Lead** | Dev 3 | Django apps, API design | Models, serializers, viewsets |
| **Backend Dev** | Dev 4 | Business logic, Celery tasks | Bracket generation, payment flow |
| **Full-stack** | Dev 5 | Bridge frontend/backend, WebSocket | Real-time features, troubleshooting |
| **QA Engineer** | QA 1 | Test automation, manual testing | Test suite, bug reports |
| **DevOps** | DevOps 1 (0.5 FTE) | CI/CD, infrastructure | Deployment pipeline, monitoring |
| **Designer** | Designer 1 (0.5 FTE) | Figma mockups, asset export | High-fidelity designs, icons |
| **PM** | PM 1 (0.5 FTE) | Sprint planning, stakeholder comms | Sprint reports, roadmap |

### 7.2 Communication Channels

**Daily Standup (15 min):**
- Time: 10:00 AM (Bangladesh time)
- Format: What I did yesterday, what I'll do today, blockers
- Platform: Slack huddle or Zoom

**Sprint Planning (2 hours):**
- Frequency: Every 2 weeks (Monday)
- Agenda: Review previous sprint, plan next sprint, assign tasks
- Artifacts: Sprint backlog, story point estimates

**Sprint Review (1 hour):**
- Frequency: End of sprint (Friday)
- Agenda: Demo completed features, gather feedback
- Attendees: Team + stakeholders

**Retrospective (1 hour):**
- Frequency: After sprint review
- Format: What went well, what didn't, action items
- Tools: Miro board

**Tech Sync (1 hour):**
- Frequency: Weekly (Wednesday)
- Topics: Architecture decisions, code reviews, technical blockers
- Attendees: Developers only

### 7.3 Development Workflow

```
1. Task Assignment (Jira)
   ├─> Create branch: feature/FE-001-button-component
   ├─> Implement feature
   ├─> Write tests (80% coverage)
   └─> Local testing

2. Code Review (GitHub PR)
   ├─> Create pull request
   ├─> CI/CD runs (tests, lint, build)
   ├─> Code review (2 approvals required)
   └─> Address feedback

3. Merge & Deploy
   ├─> Merge to develop branch
   ├─> Auto-deploy to staging
   ├─> QA testing on staging
   └─> Merge to main (production)
```

---

## 8. Integration Checklist & Dependencies

### 8.1 Part 2 (Architecture) Integration

| Architecture Component | Implementation Status | Location | Notes |
|------------------------|----------------------|----------|-------|
| **Django Apps** | ✅ Structure defined | `apps/` folder | See Sprint 1 tasks |
| **REST API** | ✅ Endpoints mapped | Section 4.2 | DRF viewsets |
| **WebSocket** | ✅ Channels configured | Section 4.3 | Django Channels + Redis |
| **Celery Tasks** | ✅ Task list defined | Section 4.5 | Email, certificates, cron jobs |
| **Database Schema** | ✅ Models created | Part 3 reference | Migrations in Sprint 1-2 |
| **Authentication** | ✅ JWT + Session | Section 4.2 | Allauth integration |
| **File Storage** | 🔄 S3 or local | Sprint 3 | Payment proofs, certificates |
| **Email Service** | 🔄 SMTP or SendGrid | Sprint 3 | Notifications |

### 8.2 Part 3 (Database) Integration

| Database Model | Sprint | Dependencies | Status |
|----------------|--------|--------------|--------|
| **User & Profile** | Sprint 1 | Auth system | ✅ Core |
| **Tournament** | Sprint 2 | User | ✅ Core |
| **Game Config** | Sprint 2 | - | ✅ Core |
| **Registration** | Sprint 3 | Tournament, Team | ✅ Phase 2 |
| **Payment** | Sprint 3 | Registration | ✅ Phase 2 |
| **Bracket** | Sprint 4 | Tournament | ✅ Phase 2 |
| **Match** | Sprint 4 | Bracket, Team | ✅ Phase 2 |
| **Certificate** | Sprint 6 | Tournament, User | ✅ Phase 3 |
| **Discussion** | Sprint 6 | Tournament, User | ✅ Phase 3 |
| **Notification** | Sprint 5 | User | ✅ Phase 3 |

### 8.3 Part 4 (UI/UX) Integration

| UI Component | Frontend Task | Backend API | Status |
|--------------|---------------|-------------|--------|
| **Navbar** | FE-002 | `/api/v1/users/profile/` | ✅ Sprint 1 |
| **Tournament Card** | FE-010 | `/api/v1/tournaments/` | ✅ Sprint 2 |
| **Registration Form** | FE-018 | `/api/v1/registrations/` | ✅ Sprint 3 |
| **Payment Panel** | FE-021 | `/api/v1/payments/` | ✅ Sprint 3 |
| **Bracket Display** | FE-026 | `/api/v1/tournaments/{id}/bracket/` | ✅ Sprint 4 |
| **Match Card** | FE-028 | `/api/v1/matches/{id}/` | ✅ Sprint 4 |
| **Live HUD** | FE-034 | WebSocket consumer | ✅ Sprint 5 |
| **Certificate View** | FE-044 | `/api/v1/certificates/{id}/` | ✅ Sprint 6 |

---

## 9. Post-Launch & Iteration Plan

### 9.1 Monitoring Metrics

**Application Metrics (DataDog/Prometheus):**

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| **Request Rate** | 100 req/s | >500 req/s |
| **Error Rate** | <1% | >5% (5 min) |
| **Response Time (p95)** | <200ms | >500ms |
| **WebSocket Connections** | 100+ concurrent | Connection drops >10/min |
| **Celery Queue Length** | <50 | >500 tasks pending |
| **Database Connections** | <80% pool | >90% pool usage |

**Business Metrics (Google Analytics 4):**

| Metric | Week 1 Target | Month 1 Target |
|--------|---------------|----------------|
| **Tournaments Created** | 10 | 100 |
| **Teams Registered** | 50 | 500 |
| **Payment Submissions** | 40 | 400 |
| **Certificates Issued** | 20 | 200 |
| **Active Users (DAU)** | 100 | 1,000 |
| **Spectator Views** | 200 | 2,000 |

### 9.2 User Feedback Collection

**In-App Feedback Widget:**
- Location: Bottom-right corner (all pages)
- Types: Bug report, feature request, general feedback
- Integration: Typeform or Google Forms

**Post-Tournament Survey:**
- Trigger: 24 hours after tournament completion
- Questions: Satisfaction (1-5), improvements, issues
- Incentive: Entry into raffle for ৳500 DeltaCoin

**Beta User Interviews:**
- Frequency: Weekly (first month)
- Participants: 5-10 organizers and players
- Format: 30-minute video call, structured questions

### 9.3 Feature Iteration Roadmap

**Phase 5 (Weeks 17-20): Post-Launch Improvements**

Based on user feedback:

| Feature | Priority | Effort | Impact |
|---------|----------|--------|--------|
| **Mobile App (PWA)** | High | 8 weeks | High |
| **Advanced Analytics Dashboard** | Medium | 4 weeks | Medium |
| **Sponsor Management Module** | Medium | 3 weeks | High (revenue) |
| **Team Rankings System** | High | 2 weeks | Medium |
| **Discord Bot Integration** | Low | 2 weeks | Medium |
| **Payment Gateway (bKash API)** | High | 6 weeks | High (automation) |
| **Automated Bracket Broadcasting** | Medium | 4 weeks | Medium |

### 9.4 Maintenance Schedule

**Daily:**
- Monitor error logs (Sentry)
- Check server health (uptime, CPU, memory)
- Review user feedback submissions

**Weekly:**
- Database backup verification
- Dependency security updates
- Performance report review

**Monthly:**
- Full security audit
- Database optimization (vacuum, reindex)
- User analytics report
- Stakeholder update meeting

### 9.5 Scaling Plan

**When to Scale (Triggers):**
- >500 concurrent users (current: 100)
- >1,000 tournaments/month (current: 100)
- Response time >500ms (current: <200ms)

**Scaling Actions:**
- **Horizontal scaling:** Add 2 more web servers (load balanced)
- **Database:** Upgrade to 8GB RAM, read replicas
- **CDN:** Enable full CDN for static/media (Cloudflare)
- **Cache layer:** Expand Redis cache (8GB)

---

## 10. Appendix: Technical Reference

### 10.1 Key Dependencies

**Python (requirements.txt):**
```
Django==4.2.7
djangorestframework==3.14.0
django-allauth==0.57.0
django-cors-headers==4.3.0
djangorestframework-simplejwt==5.3.0
channels==4.0.0
channels-redis==4.1.0
celery==5.3.4
redis==5.0.1
psycopg2-binary==2.9.9
Pillow==10.1.0
gunicorn==21.2.0
sentry-sdk==1.38.0
pytest==7.4.3
pytest-django==4.7.0
pytest-cov==4.1.0
```

**JavaScript (package.json):**
```json
{
  "dependencies": {
    "htmx.org": "^1.9.10",
    "alpinejs": "^3.13.3",
    "chart.js": "^4.4.0"
  },
  "devDependencies": {
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.32",
    "autoprefixer": "^10.4.16",
    "webpack": "^5.89.0",
    "@tailwindcss/forms": "^0.5.7",
    "@tailwindcss/typography": "^0.5.10"
  }
}
```

### 10.2 Environment Variables

**.env.example:**
```bash
# Django
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=deltacrown.com,www.deltacrown.com

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/deltacrown

# Redis
REDIS_URL=redis://localhost:6379/0

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@deltacrown.com
EMAIL_HOST_PASSWORD=your-password

# AWS S3 (optional)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_STORAGE_BUCKET_NAME=deltacrown-media

# Sentry
SENTRY_DSN=https://your-sentry-dsn

# Environment
ENVIRONMENT=production
```

### 10.3 Useful Commands

```bash
# Development
python manage.py runserver
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py shell_plus

# Testing
pytest
pytest --cov=apps
pytest -v -s tests/test_tournaments.py

# Frontend
npm run dev
npm run build
npm run lint

# Celery
celery -A deltacrown worker -l info
celery -A deltacrown beat -l info

# Docker
docker-compose up -d
docker-compose logs -f web
docker-compose exec web python manage.py migrate
docker-compose down

# Deployment
./deploy.sh
python manage.py collectstatic --noinput
python manage.py compress
```

---

## Conclusion

This Implementation Roadmap provides a comprehensive, actionable plan for building the DeltaCrown Tournament Engine over 16 weeks. Key achievements:

✅ **4 phases, 8 sprints** with detailed task breakdown (200+ tasks)  
✅ **Clear dependencies** mapped across Parts 2-4  
✅ **Testing strategy** with 80%+ coverage targets  
✅ **CI/CD pipeline** with blue-green deployment  
✅ **Team structure** with defined roles and workflows  
✅ **Post-launch plan** with monitoring, feedback, and iteration  

**Next Steps:**
1. ✅ **Sprint 0 (Prep Week):** Set up repositories, tools, environments
2. ✅ **Sprint 1 (Week 1-2):** Begin Phase 1 - Foundation
3. 📈 **Track Progress:** Daily standups, weekly demos, sprint reviews
4. 🚀 **Launch (Week 16):** Production deployment + marketing campaign

**Success Metrics:**
- Timeline: On schedule (±1 week acceptable)
- Quality: <5 P2 bugs in first week of production
- Performance: Lighthouse scores >90
- User satisfaction: >80% positive feedback from beta users

---

**Document Status:** ✅ **COMPLETE** - Ready for Team Review  
**Total Pages:** 100+ (comprehensive implementation guide)  
**Word Count:** ~15,000 words  
**Prepared by:** Implementation Team  
**Review Date:** November 3, 2025  
**Approved for Execution:** Pending stakeholder sign-off

---

**Navigation:**
- [← Previous: PART_5.1 - Implementation Roadmap & Sprint Planning](./PART_5.1_IMPLEMENTATION_ROADMAP_SPRINT_PLANNING.md)
- [↑ Back to Index](./INDEX_MASTER_NAVIGATION.md)
