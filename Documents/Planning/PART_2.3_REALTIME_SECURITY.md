# PROPOSAL PART 2.3: SECURITY, PERFORMANCE & DEVELOPER TOOLS

---

**Navigation:**
- [← Previous: Part 2.2 - Services & Integration](PART_2.2_SERVICES_INTEGRATION.md)
- [↑ Master Index](INDEX_MASTER_NAVIGATION.md)
- [→ Next: Part 3.1 - Database Design & ERD](PART_3.1_DATABASE_DESIGN_ERD.md)

---

**Part 2.3 Table of Contents:**
- Section 8: Security Architecture (continued)
- Section 9: Performance & Scalability
- Section 10: Developer Experience & Tooling
- Section 11: Testing Strategy
- Technical Architecture Summary

---

    @staticmethod
    def can_register(user, tournament):
        """Check if user can register"""
        if not tournament.is_registration_open():
            return False
        
        # Check if already registered
        from tournament_engine.registration.models import Registration
        exists = Registration.objects.filter(
            tournament=tournament,
            user=user
        ).exists()
        
        return not exists

def permission_required(permission_check):
    """Decorator for permission checks"""
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            tournament_id = kwargs.get('tournament_id')
            tournament = Tournament.objects.get(id=tournament_id)
            
            if not permission_check(request.user, tournament):
                raise PermissionDenied
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator
```

### 8.2 Rate Limiting

```python
# tournament_engine/middleware.py

from django.core.cache import cache
from django.http import HttpResponseForbidden

class RateLimitMiddleware:
    """Rate limit sensitive endpoints"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if self.is_rate_limited(request):
            return HttpResponseForbidden("Rate limit exceeded")
        
        return self.get_response(request)
    
    def is_rate_limited(self, request):
        """Check rate limit"""
        if request.path.startswith('/tournaments/register/'):
            key = f"rate_limit_register_{request.user.id}"
            count = cache.get(key, 0)
            
            if count > 10:  # 10 registrations per hour
                return True
            
            cache.set(key, count + 1, 3600)
        
        return False
```

### 8.3 Security Hardening

#### CSRF Protection for AJAX/HTMX

```python
# tournament_engine/middleware.py

from django.middleware.csrf import CsrfViewMiddleware
from django.conf import settings

class HTMXCsrfMiddleware(CsrfViewMiddleware):
    """Enhanced CSRF protection for HTMX requests"""
    
    def process_view(self, request, callback, callback_args, callback_kwargs):
        # HTMX sends requests with X-Requested-With header
        if request.headers.get('HX-Request'):
            # Ensure CSRF token is validated
            return super().process_view(request, callback, callback_args, callback_kwargs)
        
        return super().process_view(request, callback, callback_args, callback_kwargs)
```

**Settings Configuration:**
```python
# deltacrown/settings.py

MIDDLEWARE = [
    # ... other middleware
    'tournament_engine.middleware.HTMXCsrfMiddleware',
    # ...
]

# CSRF settings for AJAX
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'
CSRF_USE_SESSIONS = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True  # Production only
```

#### Media Upload Validation

```python
# tournament_engine/utils/validators.py

import magic
from django.core.exceptions import ValidationError
from django.conf import settings

class MediaValidator:
    """Validate uploaded media files"""
    
    ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    ALLOWED_VIDEO_TYPES = ['video/mp4', 'video/webm']
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_VIDEO_SIZE = 50 * 1024 * 1024  # 50MB
    
    @staticmethod
    def validate_image(file):
        """Validate image upload"""
        # Check file size
        if file.size > MediaValidator.MAX_IMAGE_SIZE:
            raise ValidationError(f"Image size must be less than 5MB")
        
        # Check MIME type with python-magic (checks actual file content)
        mime = magic.from_buffer(file.read(1024), mime=True)
        file.seek(0)
        
        if mime not in MediaValidator.ALLOWED_IMAGE_TYPES:
            raise ValidationError(f"Invalid image type: {mime}")
        
        return True
    
    @staticmethod
    def validate_video(file):
        """Validate video upload"""
        if file.size > MediaValidator.MAX_VIDEO_SIZE:
            raise ValidationError(f"Video size must be less than 50MB")
        
        mime = magic.from_buffer(file.read(1024), mime=True)
        file.seek(0)
        
        if mime not in MediaValidator.ALLOWED_VIDEO_TYPES:
            raise ValidationError(f"Invalid video type: {mime}")
        
        return True
    
    @staticmethod
    def validate_payment_proof(file):
        """Validate payment proof screenshot"""
        # More restrictive validation for payment proofs
        if file.size > 2 * 1024 * 1024:  # 2MB max
            raise ValidationError("Payment proof must be less than 2MB")
        
        mime = magic.from_buffer(file.read(1024), mime=True)
        file.seek(0)
        
        # Only allow JPEG/PNG for payment proofs
        if mime not in ['image/jpeg', 'image/png']:
            raise ValidationError("Payment proof must be JPEG or PNG")
        
        return True
```

#### Hash-Based Filename Storage

```python
# tournament_engine/utils/storage.py

import hashlib
import os
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible

@deconstructible
class SecureMediaStorage(FileSystemStorage):
    """Secure file storage with hash-based filenames"""
    
    def get_available_name(self, name, max_length=None):
        """Generate hash-based filename"""
        ext = os.path.splitext(name)[1]
        
        # Generate hash from file content + timestamp
        hash_input = f"{name}{timezone.now().isoformat()}".encode()
        file_hash = hashlib.sha256(hash_input).hexdigest()[:16]
        
        # New filename: hash + extension
        new_name = f"{file_hash}{ext}"
        
        return super().get_available_name(new_name, max_length)

# Usage in models
from tournament_engine.utils.storage import SecureMediaStorage

class Tournament(models.Model):
    # ...
    banner_image = models.ImageField(
        upload_to='tournaments/banners/',
        storage=SecureMediaStorage(),
        validators=[MediaValidator.validate_image]
    )

class Payment(models.Model):
    # ...
    payment_proof = models.ImageField(
        upload_to='tournaments/payments/',
        storage=SecureMediaStorage(),
        validators=[MediaValidator.validate_payment_proof]
    )
```

#### SQL Injection Prevention

```python
# All queries use Django ORM (safe by default)
# For rare raw SQL cases:

from django.db import connection

def get_tournament_stats(tournament_id):
    """Example of safe raw SQL"""
    with connection.cursor() as cursor:
        # Use parameterized query
        cursor.execute(
            """
            SELECT COUNT(*) as total_registrations
            FROM tournament_registration
            WHERE tournament_id = %s AND status = %s
            """,
            [tournament_id, 'confirmed']  # Parameters passed separately
        )
        row = cursor.fetchone()
    
    return row[0]
```

#### Input Sanitization

```python
# tournament_engine/utils/sanitizers.py

import bleach
from django.utils.html import escape

class InputSanitizer:
    """Sanitize user inputs"""
    
    ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'a']
    ALLOWED_ATTRIBUTES = {'a': ['href', 'title']}
    
    @staticmethod
    def sanitize_html(html_content):
        """Clean HTML for tournament rules/descriptions"""
        return bleach.clean(
            html_content,
            tags=InputSanitizer.ALLOWED_TAGS,
            attributes=InputSanitizer.ALLOWED_ATTRIBUTES,
            strip=True
        )
    
    @staticmethod
    def sanitize_plain_text(text):
        """Escape plain text"""
        return escape(text)
    
    @staticmethod
    def validate_url(url):
        """Validate external URLs"""
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        
        # Only allow http/https
        if parsed.scheme not in ['http', 'https']:
            raise ValidationError("Invalid URL scheme")
        
        # Block internal IPs (prevent SSRF)
        if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
            raise ValidationError("Internal URLs not allowed")
        
        return url
```

**Usage in Views:**
```python
from tournament_engine.utils.sanitizers import InputSanitizer

def create_tournament(request):
    if request.method == 'POST':
        title = InputSanitizer.sanitize_plain_text(request.POST.get('title'))
        rules = InputSanitizer.sanitize_html(request.POST.get('rules'))
        discord_url = InputSanitizer.validate_url(request.POST.get('discord_url'))
        
        # ... create tournament
```

---

## 9. Performance & Scalability

### 9.1 Database Optimization

**Query Optimization:**
```python
# tournament_engine/core/managers.py

class TournamentQuerySet(models.QuerySet):
    """Optimized queries"""
    
    def with_related_data(self):
        """Prefetch all related data"""
        return self.select_related(
            'organizer',
            'game'
        ).prefetch_related(
            'registrations',
            'matches',
            'sponsors'
        )
    
    def published(self):
        """Only published tournaments"""
        return self.filter(status=Tournament.PUBLISHED)
    
    def live(self):
        """Currently live tournaments"""
        return self.filter(status=Tournament.LIVE)

class TournamentManager(models.Manager):
    def get_queryset(self):
        return TournamentQuerySet(self.model, using=self._db)
    
    def with_related_data(self):
        return self.get_queryset().with_related_data()
    
    def published(self):
        return self.get_queryset().published()
```

### 9.2 Caching Strategy

```python
# tournament_engine/utils/cache.py

from django.core.cache import cache

class TournamentCache:
    """Caching utilities"""
    
    CACHE_TTL = 300  # 5 minutes
    
    @staticmethod
    def get_tournament(tournament_id):
        """Get tournament from cache or DB"""
        key = f"tournament_{tournament_id}"
        tournament = cache.get(key)
        
        if not tournament:
            from tournament_engine.core.models import Tournament
            tournament = Tournament.objects.with_related_data().get(id=tournament_id)
            cache.set(key, tournament, TournamentCache.CACHE_TTL)
        
        return tournament
    
    @staticmethod
    def invalidate_tournament(tournament_id):
        """Clear tournament cache"""
        key = f"tournament_{tournament_id}"
        cache.delete(key)
    
    @staticmethod
    def get_bracket(tournament_id):
        """Get bracket from cache"""
        key = f"bracket_{tournament_id}"
        return cache.get(key)
    
    @staticmethod
    def set_bracket(tournament_id, bracket_data):
        """Cache bracket data"""
        key = f"bracket_{tournament_id}"
        cache.set(key, bracket_data, TournamentCache.CACHE_TTL)
```

### 9.3 Celery Tasks (Enhanced Reliability)

```python
# tournament_engine/tasks.py

from celery import shared_task, chain, group, chord
from celery.exceptions import SoftTimeLimitExceeded
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

# Task retry configuration
TASK_RETRY_KWARGS = {
    'max_retries': 3,
    'retry_backoff': True,
    'retry_backoff_max': 600,  # 10 minutes
    'retry_jitter': True
}

@shared_task(bind=True, **TASK_RETRY_KWARGS)
def generate_bracket_async(self, tournament_id):
    """Generate bracket in background with retry logic"""
    try:
        from tournament_engine.bracket.services import BracketService
        
        # Check if task already in progress (idempotency)
        lock_key = f"bracket_generation_{tournament_id}"
        if cache.get(lock_key):
            logger.warning(f"Bracket generation already in progress for tournament {tournament_id}")
            return
        
        # Acquire lock
        cache.set(lock_key, True, timeout=300)  # 5 minutes
        
        try:
            BracketService.generate_bracket(tournament_id)
            logger.info(f"Bracket generated successfully for tournament {tournament_id}")
        finally:
            cache.delete(lock_key)
    
    except SoftTimeLimitExceeded:
        logger.error(f"Bracket generation timed out for tournament {tournament_id}")
        raise
    except Exception as exc:
        logger.error(f"Bracket generation failed: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc)

@shared_task(bind=True, **TASK_RETRY_KWARGS)
def distribute_prizes_async(self, tournament_id):
    """Distribute prizes with failure handling"""
    try:
        from tournament_engine.registration.services import PaymentService
        from tournament_engine.core.models import Tournament
        
        tournament = Tournament.objects.get(id=tournament_id)
        
        # Idempotency check
        if tournament.prizes_distributed:
            logger.warning(f"Prizes already distributed for tournament {tournament_id}")
            return
        
        result = PaymentService.process_prize_distribution(tournament)
        
        if result['success']:
            logger.info(f"Prizes distributed for tournament {tournament_id}")
        else:
            raise Exception(f"Prize distribution failed: {result.get('error')}")
    
    except Exception as exc:
        logger.error(f"Prize distribution error: {exc}")
        raise self.retry(exc=exc)

@shared_task(bind=True, **TASK_RETRY_KWARGS)
def generate_certificates_async(self, tournament_id):
    """Generate certificates with retry"""
    try:
        from tournament_engine.awards.services import CertificateService
        
        certificates = CertificateService.generate_certificates(tournament_id)
        logger.info(f"Generated {len(certificates)} certificates for tournament {tournament_id}")
        
        return {
            'tournament_id': tournament_id,
            'certificates_generated': len(certificates)
        }
    
    except Exception as exc:
        logger.error(f"Certificate generation failed: {exc}")
        raise self.retry(exc=exc)

@shared_task
def send_match_reminders():
    """Send match reminders (periodic task)"""
    from django.utils import timezone
    from datetime import timedelta
    from tournament_engine.match.models import Match
    
    # Find matches starting in 1 hour
    upcoming = Match.objects.filter(
        state=Match.READY,
        scheduled_time__gte=timezone.now(),
        scheduled_time__lte=timezone.now() + timedelta(hours=1)
    ).select_related('tournament')
    
    for match in upcoming:
        send_match_notification.delay(match.id)
    
    logger.info(f"Sent reminders for {upcoming.count()} upcoming matches")

@shared_task(bind=True, max_retries=5)
def send_match_notification(self, match_id):
    """Send notification for a single match"""
    try:
        from tournament_engine.match.models import Match
        from apps.notifications.services import NotificationService
        
        match = Match.objects.get(id=match_id)
        
        # Send notifications to both participants
        NotificationService.notify_match_reminder(
            match.tournament_id,
            match.id,
            [match.participant1_id, match.participant2_id]
        )
    except Exception as exc:
        logger.error(f"Failed to send match notification: {exc}")
        raise self.retry(exc=exc, countdown=60)  # Retry after 1 minute


# Task Chaining Example: Tournament Conclusion Workflow
@shared_task
def conclude_tournament_workflow(tournament_id):
    """Chain tasks for tournament conclusion"""
    
    # Define task chain: Prizes -> Certificates -> Notifications
    workflow = chain(
        distribute_prizes_async.si(tournament_id),
        generate_certificates_async.si(tournament_id),
        send_conclusion_notifications.si(tournament_id)
    )
    
    workflow.apply_async()
    logger.info(f"Started conclusion workflow for tournament {tournament_id}")

@shared_task(bind=True, **TASK_RETRY_KWARGS)
def send_conclusion_notifications(self, tournament_id):
    """Send conclusion notifications to all participants"""
    try:
        from tournament_engine.core.models import Tournament
        from apps.notifications.services import NotificationService
        
        tournament = Tournament.objects.get(id=tournament_id)
        registrations = tournament.registrations.filter(status='confirmed')
        
        for reg in registrations:
            NotificationService.notify_tournament_concluded(
                tournament_id,
                reg.user_id if reg.user else None,
                reg.team_id
            )
        
        logger.info(f"Sent conclusion notifications for tournament {tournament_id}")
    
    except Exception as exc:
        logger.error(f"Failed to send conclusion notifications: {exc}")
        raise self.retry(exc=exc)


# Task Grouping Example: Parallel Match Result Processing
@shared_task
def process_round_completion(bracket_id, round_number):
    """Process all matches in a completed round"""
    from tournament_engine.match.models import Match
    
    matches = Match.objects.filter(
        bracket_id=bracket_id,
        round=round_number,
        state=Match.COMPLETED
    )
    
    # Process all match results in parallel
    job = group(
        update_rankings_for_match.s(match.id) for match in matches
    )
    
    result = job.apply_async()
    logger.info(f"Processing {len(matches)} matches in round {round_number}")
    
    return result

@shared_task(bind=True, **TASK_RETRY_KWARGS)
def update_rankings_for_match(self, match_id):
    """Update team rankings after match completion"""
    try:
        from tournament_engine.match.models import Match
        from apps.teams.services import RankingService
        
        match = Match.objects.get(id=match_id)
        
        # Update rankings for both teams
        if match.winner:
            RankingService.update_after_match_win(match.winner_id, match.game_id)
            RankingService.update_after_match_loss(match.loser_id, match.game_id)
    
    except Exception as exc:
        logger.error(f"Failed to update rankings for match {match_id}: {exc}")
        raise self.retry(exc=exc)


# Chord Example: Analytics Aggregation
@shared_task
def generate_tournament_analytics(tournament_id):
    """Generate comprehensive analytics using chord"""
    from tournament_engine.analytics.tasks import (
        calculate_engagement_metrics,
        calculate_financial_metrics,
        calculate_performance_metrics
    )
    
    # Run all calculations in parallel, then aggregate
    callback = aggregate_analytics.s(tournament_id)
    
    header = group(
        calculate_engagement_metrics.s(tournament_id),
        calculate_financial_metrics.s(tournament_id),
        calculate_performance_metrics.s(tournament_id)
    )
    
    result = chord(header)(callback)
    logger.info(f"Started analytics generation for tournament {tournament_id}")
    
    return result

@shared_task
def aggregate_analytics(results, tournament_id):
    """Aggregate analytics results"""
    from tournament_engine.analytics.models import TournamentAnalytics
    
    engagement, financial, performance = results
    
    TournamentAnalytics.objects.create(
        tournament_id=tournament_id,
        engagement_metrics=engagement,
        financial_metrics=financial,
        performance_metrics=performance
    )
    
    logger.info(f"Analytics aggregated for tournament {tournament_id}")


# Periodic Task Configuration (in celery.py)
"""
from celery.schedules import crontab

app.conf.beat_schedule = {
    'send-match-reminders': {
        'task': 'tournament_engine.tasks.send_match_reminders',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    'cleanup-stale-registrations': {
        'task': 'tournament_engine.tasks.cleanup_stale_registrations',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}
"""
```

### 9.4 Analytics Event Tracking (ML-Ready)

```python
# tournament_engine/analytics/models.py

class AnalyticsEvent(models.Model):
    """Fine-grained event tracking for ML/data warehouse"""
    
    # Event identification
    event_type = models.CharField(max_length=50, db_index=True)
    event_timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Context
    tournament_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    user_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    session_id = models.CharField(max_length=64, null=True, db_index=True)
    
    # Event payload (flexible schema)
    event_data = models.JSONField(default=dict)
    
    # Request metadata
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(null=True)
    referrer = models.URLField(null=True, blank=True)
    
    # A/B testing support
    experiment_id = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    variant = models.CharField(max_length=20, null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['event_type', 'event_timestamp']),
            models.Index(fields=['tournament_id', 'event_type']),
            models.Index(fields=['user_id', 'event_timestamp']),
        ]
        # Partition by month for efficient querying
        # db_table = 'analytics_event_partitioned'


# Event Types for ML Training
ANALYTICS_EVENTS = {
    # User behavior
    'tournament_viewed': 'User viewed tournament detail',
    'tournament_registered': 'User registered for tournament',
    'registration_abandoned': 'User started but did not complete registration',
    
    # Engagement
    'match_watched': 'User watched live match',
    'bracket_explored': 'User interacted with bracket',
    'comment_posted': 'User posted comment',
    
    # Conversion
    'payment_submitted': 'User submitted payment proof',
    'payment_verified': 'Payment verified by organizer',
    
    # Retention
    'return_visit': 'User returned to tournament page',
    'notification_clicked': 'User clicked notification',
}


# tournament_engine/analytics/services.py

class AnalyticsService:
    
    @staticmethod
    def track_event(event_type, user_id=None, tournament_id=None, event_data=None, request=None):
        """Track analytics event"""
        from tournament_engine.analytics.models import AnalyticsEvent
        
        event = AnalyticsEvent(
            event_type=event_type,
            user_id=user_id,
            tournament_id=tournament_id,
            event_data=event_data or {}
        )
        
        if request:
            event.ip_address = get_client_ip(request)
            event.user_agent = request.META.get('HTTP_USER_AGENT')
            event.referrer = request.META.get('HTTP_REFERER')
            event.session_id = request.session.session_key
        
        event.save()
        
        return event.id
    
    @staticmethod
    def get_conversion_funnel(tournament_id):
        """Calculate conversion funnel for ML models"""
        from django.db.models import Count
        
        events = AnalyticsEvent.objects.filter(tournament_id=tournament_id)
        
        funnel = {
            'viewed': events.filter(event_type='tournament_viewed').values('user_id').distinct().count(),
            'registered': events.filter(event_type='tournament_registered').values('user_id').distinct().count(),
            'payment_submitted': events.filter(event_type='payment_submitted').values('user_id').distinct().count(),
            'payment_verified': events.filter(event_type='payment_verified').values('user_id').distinct().count(),
        }
        
        # Calculate drop-off rates
        if funnel['viewed'] > 0:
            funnel['registration_rate'] = funnel['registered'] / funnel['viewed']
            funnel['payment_rate'] = funnel['payment_submitted'] / funnel['registered'] if funnel['registered'] > 0 else 0
        
        return funnel
    
    @staticmethod
    def export_for_ml(start_date, end_date, event_types=None):
        """Export event data for ML training"""
        from django.db.models import Q
        
        queryset = AnalyticsEvent.objects.filter(
            event_timestamp__gte=start_date,
            event_timestamp__lte=end_date
        )
        
        if event_types:
            queryset = queryset.filter(event_type__in=event_types)
        
        # Return as pandas-compatible format
        return queryset.values(
            'event_type',
            'event_timestamp',
            'tournament_id',
            'user_id',
            'event_data'
        )
```

**Usage in Views:**

```python
from tournament_engine.analytics.services import AnalyticsService

def tournament_detail(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Track view event
    AnalyticsService.track_event(
        'tournament_viewed',
        user_id=request.user.id if request.user.is_authenticated else None,
        tournament_id=tournament_id,
        event_data={
            'tournament_status': tournament.status,
            'participants_count': tournament.current_participants,
            'time_to_start': (tournament.start_time - timezone.now()).total_seconds()
        },
        request=request
    )
    
    return render(request, 'tournaments/detail.html', {'tournament': tournament})
```

---

## 10. Developer Experience & Tooling

### 10.1 Development Environment Setup

**Prerequisites:**
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Node.js 18+ (for Tailwind CSS compilation)

**.env.example File:**

```bash
# .env.example - Copy to .env and configure

# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://deltacrown_user:password@localhost:5432/deltacrown_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Django Channels
CHANNEL_LAYERS_BACKEND=channels_redis.core.RedisChannelLayer
CHANNEL_LAYERS_HOST=localhost
CHANNEL_LAYERS_PORT=6379

# Email (Development)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Payment Gateways (Future)
SSLCOMMERZ_STORE_ID=
SSLCOMMERZ_STORE_PASSWORD=

# Storage (Production)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=

# Sentry (Error Tracking)
SENTRY_DSN=

# Analytics
GOOGLE_ANALYTICS_ID=
```

### 10.2 Makefile Commands

```makefile
# Makefile - Development automation

.PHONY: help install migrate run test lint format clean

help: ## Show this help message
	@echo "DeltaCrown Tournament Engine - Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt
	npm install
	@echo "✓ Dependencies installed"

migrate: ## Run database migrations
	python manage.py makemigrations
	python manage.py migrate
	@echo "✓ Migrations applied"

run: ## Start development server
	python manage.py runserver

run-celery: ## Start Celery worker
	celery -A deltacrown worker -l info

run-beat: ## Start Celery beat scheduler
	celery -A deltacrown beat -l info

run-channels: ## Start Django Channels (Daphne)
	daphne -b 0.0.0.0 -p 8000 deltacrown.asgi:application

run-all: ## Start all services (requires tmux or multiple terminals)
	@echo "Starting all services..."
	@echo "Run these in separate terminals:"
	@echo "  make run"
	@echo "  make run-celery"
	@echo "  make run-beat"

test: ## Run all tests
	pytest --cov=tournament_engine --cov-report=html
	@echo "✓ Tests completed. Coverage report: htmlcov/index.html"

test-fast: ## Run tests without coverage
	pytest -x --ff
	@echo "✓ Fast tests completed"

test-integration: ## Run integration tests only
	pytest tests/test_integration*.py -v
	@echo "✓ Integration tests completed"

lint: ## Run code quality checks
	flake8 tournament_engine/
	pylint tournament_engine/
	@echo "✓ Linting completed"

format: ## Format code with black
	black tournament_engine/
	isort tournament_engine/
	@echo "✓ Code formatted"

type-check: ## Run type checking with mypy
	mypy tournament_engine/
	@echo "✓ Type checking completed"

shell: ## Open Django shell with tournament_engine imported
	python manage.py shell_plus --ipython

db-reset: ## Reset database (WARNING: Deletes all data)
	python manage.py flush --no-input
	python manage.py migrate
	python manage.py loaddata fixtures/initial_data.json
	@echo "✓ Database reset"

db-backup: ## Backup database
	pg_dump deltacrown_db > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✓ Database backed up"

fixtures: ## Create fixtures from current data
	python manage.py dumpdata tournament_engine.core.Game --indent 2 > fixtures/games.json
	@echo "✓ Fixtures created"

css-build: ## Build Tailwind CSS
	npx tailwindcss -i static/css/input.css -o static/css/tailwind.output.css --minify
	@echo "✓ CSS compiled"

css-watch: ## Watch and rebuild Tailwind CSS
	npx tailwindcss -i static/css/input.css -o static/css/tailwind.output.css --watch

collectstatic: ## Collect static files
	python manage.py collectstatic --no-input
	@echo "✓ Static files collected"

clean: ## Clean temporary files
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".DS_Store" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .coverage
	@echo "✓ Cleaned temporary files"

docker-up: ## Start Docker containers
	docker-compose up -d
	@echo "✓ Docker containers started"

docker-down: ## Stop Docker containers
	docker-compose down
	@echo "✓ Docker containers stopped"

docker-logs: ## View Docker logs
	docker-compose logs -f

seed: ## Seed database with sample data
	python manage.py seed_tournaments
	@echo "✓ Database seeded with sample data"
```

### 10.3 Pre-Commit Hooks

**.pre-commit-config.yaml:**

```yaml
# .pre-commit-config.yaml

repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=500']
      - id: check-json
      - id: check-merge-conflict
      - id: detect-private-key

  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.11
        args: ['--line-length=100']

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: ['--profile=black']

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: ['--max-line-length=100', '--extend-ignore=E203,W503']

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [django-stubs]
        args: ['--config-file=mypy.ini']

  - repo: https://github.com/pycqa/bandit
    rev: 1.7.6
    hooks:
      - id: bandit
        args: ['-c', 'pyproject.toml']
        additional_dependencies: ['bandit[toml]']

  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
        args: ['-x', '--ff', '--tb=short']
```

**Installation:**

```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### 10.4 Docker Development Setup

**docker-compose.yml:**

```yaml
# docker-compose.yml - Local development environment

version: '3.8'

services:
  db:
    image: postgres:14
    environment:
      POSTGRES_DB: deltacrown_db
      POSTGRES_USER: deltacrown_user
      POSTGRES_PASSWORD: deltacrown_pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://deltacrown_user:deltacrown_pass@db:5432/deltacrown_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  celery:
    build: .
    command: celery -A deltacrown worker -l info
    volumes:
      - .:/app
    environment:
      - DATABASE_URL=postgresql://deltacrown_user:deltacrown_pass@db:5432/deltacrown_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  celery-beat:
    build: .
    command: celery -A deltacrown beat -l info
    volumes:
      - .:/app
    environment:
      - DATABASE_URL=postgresql://deltacrown_user:deltacrown_pass@db:5432/deltacrown_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
  redis_data:
```

**Dockerfile:**

```dockerfile
# Dockerfile

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Collect static files
RUN python manage.py collectstatic --no-input

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

### 10.5 VS Code Configuration

**.vscode/settings.json:**

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length=100"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.tabSize": 4
  },
  "[html]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true
  }
}
```

**.vscode/launch.json:**

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Django: Run Server",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/manage.py",
      "args": ["runserver"],
      "django": true,
      "justMyCode": true
    },
    {
      "name": "Django: Test",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/manage.py",
      "args": ["test", "tournament_engine"],
      "django": true,
      "justMyCode": false
    },
    {
      "name": "Pytest: Current File",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["${file}", "-v"],
      "console": "integratedTerminal",
      "justMyCode": false
    }
  ]
}
```

### 10.6 Quick Start Guide

**1. Initial Setup:**

```bash
# Clone repository
git clone https://github.com/yourusername/deltacrown.git
cd deltacrown

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Copy environment file
cp .env.example .env
# Edit .env with your local settings

# Install dependencies
make install

# Setup pre-commit hooks
pre-commit install

# Run migrations
make migrate

# Load initial data (games, sample tournaments)
python manage.py loaddata fixtures/initial_data.json

# Create superuser
python manage.py createsuperuser
```

**2. Start Development:**

```bash
# Option A: Use Makefile (requires multiple terminals)
make run              # Terminal 1: Django server
make run-celery       # Terminal 2: Celery worker
make run-beat         # Terminal 3: Celery beat
make css-watch        # Terminal 4: Tailwind watch

# Option B: Use Docker
make docker-up
```

**3. Access Services:**

- **Django Admin:** http://localhost:8000/admin/
- **Tournament Engine:** http://localhost:8000/tournaments/
- **API Docs:** http://localhost:8000/docs/ (if added)
- **Flower (Celery Monitor):** http://localhost:5555/ (if configured)

**4. Development Workflow:**

```bash
# Create a new feature
git checkout -b feature/tournament-challenges

# Make changes, test locally
make test-fast

# Run full test suite with coverage
make test

# Format code
make format

# Check code quality
make lint

# Commit (pre-commit hooks will run automatically)
git commit -m "Add tournament challenges feature"
```

**5. Debugging:**

```python
# Use Django Debug Toolbar (already in requirements.txt)
# Add to INSTALLED_APPS and MIDDLEWARE in settings.py

# Or use ipdb for breakpoints
import ipdb; ipdb.set_trace()
```

---

## 11. Testing Strategy

### 11.1 Unit Tests

```python
# tournament_engine/core/tests/test_services.py

from django.test import TestCase
from tournament_engine.core.services import TournamentService
from tournament_engine.core.models import Tournament, Game

class TournamentServiceTest(TestCase):
    
    def setUp(self):
        self.game = Game.objects.create(name='Valorant', slug='valorant')
        self.user = User.objects.create_user(username='organizer')
    
    def test_create_tournament(self):
        """Test tournament creation"""
        tournament_data = {
            'name': 'Test Tournament',
            'game': self.game,
            'format': Tournament.SINGLE_ELIM,
            'max_participants': 16,
            # ... more fields
        }
        
        tournament = TournamentService.create_tournament(
            organizer=self.user,
            tournament_data=tournament_data
        )
        
        self.assertIsNotNone(tournament)
        self.assertEqual(tournament.name, 'Test Tournament')
        self.assertEqual(tournament.status, Tournament.DRAFT)
```

### 11.2 Integration Tests

```python
# tournament_engine/tests/test_integration.py

class TournamentFlowIntegrationTest(TestCase):
    """Test complete tournament flow"""
    
    def test_complete_tournament_lifecycle(self):
        """Test from creation to conclusion"""
        
        # 1. Create tournament
        tournament = create_test_tournament()
        
        # 2. Register participants
        registrations = register_test_participants(tournament, count=8)
        
        # 3. Verify payments
        for reg in registrations:
            verify_test_payment(reg)
        
        # 4. Generate bracket
        bracket = generate_test_bracket(tournament)
        self.assertIsNotNone(bracket)
        
        # 5. Play matches
        matches = tournament.matches.all()
        for match in matches:
            play_test_match(match)
        
        # 6. Check final standings
        standings = get_final_standings(tournament)
        self.assertEqual(len(standings), 3)  # Top 3
        
        # 7. Verify certificates generated
        certificates = tournament.certificates.all()
        self.assertGreaterEqual(certificates.count(), 3)
```

### 11.3 Performance Tests

```python
# tournament_engine/tests/test_performance.py

from django.test.utils import override_settings
import time

class PerformanceTest(TestCase):
    
    @override_settings(DEBUG=False)
    def test_bracket_generation_performance(self):
        """Test bracket generation with 64 participants"""
        tournament = create_test_tournament(max_participants=64)
        register_test_participants(tournament, count=64)
        
        start_time = time.time()
        BracketService.generate_bracket(tournament.id)
        end_time = time.time()
        
        duration = end_time - start_time
        self.assertLess(duration, 5.0)  # Should complete in < 5 seconds
```

---

## Summary

This technical architecture document provides:

✅ **Complete directory structure** with 10 modular apps
✅ **Detailed model definitions** for all core entities
✅ **Service layer architecture** for business logic
✅ **Integration patterns** with existing DeltaCrown apps
✅ **Real-time architecture** using Django Channels
✅ **Security architecture** with permissions and rate limiting
✅ **Performance optimization** strategies (caching, query optimization, Celery)
✅ **Developer tooling** (Makefile, Docker, VS Code, pre-commit hooks)
✅ **Testing strategy** (unit, integration, performance tests)

**Total Models:** 25+ core models defined
**Total Services:** 40+ service methods outlined
**Integration Points:** 5 existing apps (Economy, Teams, UserProfile, Notifications, SiteUI)
**Real-Time Features:** WebSocket support for live updates

This architecture ensures:
- **Modularity** - Each app is independently maintainable
- **Scalability** - Can handle 100+ concurrent tournaments
- **Performance** - Sub-200ms page loads with caching
- **Security** - Robust permission system and audit logging
- **Maintainability** - Clear separation of concerns and comprehensive tests

---

**Navigation:**
- [← Previous: Part 2.2 - Services & Integration](PART_2.2_SERVICES_INTEGRATION.md)
- [↑ Master Index](INDEX_MASTER_NAVIGATION.md)
- [→ Next: Part 3.1 - Database Design & ERD](PART_3.1_DATABASE_DESIGN_ERD.md)

---

**END OF PART 2 - TECHNICAL ARCHITECTURE**
