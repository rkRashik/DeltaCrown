# Technical Standards & Conventions

**Project:** DeltaCrown Tournament Engine  
**Version:** 1.0  
**Last Updated:** November 7, 2025

---

## Overview

This document defines coding standards, conventions, and best practices for the DeltaCrown project. All code must adhere to these standards.

---

## 1. Python Code Standards

### 1.1 Style Guide
- Follow **PEP 8** strictly
- Use **Black** for code formatting (line length: 120)
- Use **isort** for import sorting
- Use **flake8** for linting (max-line-length = 120)
- Use **mypy** for type checking

### 1.2 Naming Conventions

```python
# Classes: PascalCase
class TournamentService:
    pass

# Functions/Methods: snake_case
def create_tournament():
    pass

# Constants: UPPER_SNAKE_CASE
MAX_TOURNAMENT_SIZE = 128

# Private methods: _leading_underscore
def _internal_helper():
    pass

# Module names: lowercase_with_underscores
# tournament_service.py
```

### 1.3 Type Hints

Always use type hints for function signatures:

```python
from typing import Optional, List
from django.contrib.auth import get_user_model

User = get_user_model()

def create_tournament(
    organizer: User,
    name: str,
    max_participants: int,
    entry_fee: Optional[int] = None
) -> Tournament:
    """Create a new tournament.
    
    Args:
        organizer: User creating the tournament
        name: Tournament name
        max_participants: Maximum number of participants
        entry_fee: Optional entry fee in coins
        
    Returns:
        Created Tournament instance
        
    Raises:
        ValidationError: If validation fails
    """
    pass
```

### 1.4 Docstrings

Use Google-style docstrings:

```python
def complex_function(param1: str, param2: int) -> bool:
    """Brief description of function.
    
    Longer description if needed. Can span multiple
    lines.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param2 is negative
        
    Example:
        >>> complex_function("test", 5)
        True
    """
    pass
```

### 1.5 Import Organization

Use isort with Black profile:

```python
# Standard library imports
import os
import sys
from typing import Optional

# Third-party imports
import redis
from celery import shared_task
from django.conf import settings
from django.db import models

# Local application imports
from apps.common.models import SoftDeleteModel
from apps.tournaments.services import TournamentService
```

---

## 2. Django Conventions

### 2.1 Model Structure

```python
from django.db import models
from apps.common.models import SoftDeleteModel, TimestampedModel

class Tournament(SoftDeleteModel, TimestampedModel):
    """Tournament model.
    
    Represents a competitive tournament with participants.
    """
    
    # Fields grouped by category
    # Basic Information
    name = models.CharField(max_length=200)
    description = models.TextField()
    
    # Relationships
    organizer = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='organized_tournaments'
    )
    game = models.ForeignKey(
        'Game',
        on_delete=models.PROTECT,
        related_name='tournaments'
    )
    
    # Dates
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    
    class Meta:
        db_table = 'tournaments'
        verbose_name = 'Tournament'
        verbose_name_plural = 'Tournaments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['game', 'start_date']),
        ]
    
    def __str__(self) -> str:
        return f"{self.name} ({self.get_status_display()})"
    
    def clean(self):
        """Model validation."""
        if self.end_date <= self.start_date:
            raise ValidationError("End date must be after start date")
    
    # Business methods
    def can_register(self, user: 'User') -> bool:
        """Check if user can register for tournament."""
        pass
    
    def is_full(self) -> bool:
        """Check if tournament has reached max participants."""
        pass
```

### 2.2 Service Layer Structure

```python
# apps/tournaments/services/tournament_service.py

from typing import Optional, Dict, Any
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.tournaments.models import Tournament

User = get_user_model()


class TournamentService:
    """Service for tournament business logic."""
    
    @staticmethod
    @transaction.atomic
    def create_tournament(
        organizer: User,
        data: Dict[str, Any]
    ) -> Tournament:
        """Create a new tournament.
        
        Args:
            organizer: User creating tournament
            data: Tournament data
            
        Returns:
            Created Tournament instance
            
        Raises:
            ValidationError: If data is invalid
        """
        # Validate
        TournamentService._validate_create_data(data)
        
        # Create
        tournament = Tournament.objects.create(
            organizer=organizer,
            **data
        )
        
        # Post-creation actions
        TournamentService._send_creation_notification(tournament)
        
        return tournament
    
    @staticmethod
    def _validate_create_data(data: Dict[str, Any]) -> None:
        """Validate tournament creation data."""
        pass
    
    @staticmethod
    def _send_creation_notification(tournament: Tournament) -> None:
        """Send notification after tournament creation."""
        pass
```

### 2.3 View Structure

```python
# apps/tournaments/views.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, DetailView
from django.http import JsonResponse

from apps.tournaments.models import Tournament
from apps.tournaments.forms import TournamentCreateForm
from apps.tournaments.services import TournamentService


class TournamentCreateView(LoginRequiredMixin, CreateView):
    """View for creating tournaments."""
    
    model = Tournament
    form_class = TournamentCreateForm
    template_name = 'tournaments/create.html'
    
    def form_valid(self, form):
        """Handle valid form submission."""
        tournament = TournamentService.create_tournament(
            organizer=self.request.user,
            data=form.cleaned_data
        )
        return self.render_to_response({
            'success': True,
            'tournament_id': str(tournament.id)
        })
```

### 2.4 URL Patterns

```python
# apps/tournaments/urls.py

from django.urls import path
from . import views

app_name = 'tournaments'

urlpatterns = [
    # List and creation
    path('', views.TournamentListView.as_view(), name='list'),
    path('create/', views.TournamentCreateView.as_view(), name='create'),
    
    # Detail views
    path('<uuid:pk>/', views.TournamentDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.TournamentUpdateView.as_view(), name='edit'),
    
    # Actions
    path('<uuid:pk>/publish/', views.TournamentPublishView.as_view(), name='publish'),
    path('<uuid:pk>/register/', views.TournamentRegisterView.as_view(), name='register'),
]
```

---

## 3. API Standards

### 3.1 REST API Structure

```python
# apps/tournaments/api/v1/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.tournaments.models import Tournament
from apps.tournaments.api.v1.serializers import TournamentSerializer
from apps.tournaments.services import TournamentService


class TournamentViewSet(viewsets.ModelViewSet):
    """API ViewSet for tournaments."""
    
    queryset = Tournament.objects.filter(is_deleted=False)
    serializer_class = TournamentSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        """Create tournament using service layer."""
        tournament = TournamentService.create_tournament(
            organizer=self.request.user,
            data=serializer.validated_data
        )
        return tournament
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish tournament."""
        tournament = self.get_object()
        TournamentService.publish_tournament(tournament, request.user)
        return Response({'status': 'published'})
```

### 3.2 Serializer Structure

```python
# apps/tournaments/api/v1/serializers.py

from rest_framework import serializers
from apps.tournaments.models import Tournament


class TournamentSerializer(serializers.ModelSerializer):
    """Serializer for Tournament model."""
    
    organizer_name = serializers.CharField(
        source='organizer.username',
        read_only=True
    )
    participant_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Tournament
        fields = [
            'id', 'name', 'description', 'organizer', 'organizer_name',
            'game', 'start_date', 'end_date', 'status',
            'participant_count', 'created_at'
        ]
        read_only_fields = ['id', 'organizer', 'created_at', 'status']
    
    def validate(self, data):
        """Cross-field validation."""
        if data['end_date'] <= data['start_date']:
            raise serializers.ValidationError(
                "End date must be after start date"
            )
        return data
```

### 3.3 API URL Structure

```python
# apps/tournaments/api/v1/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('tournaments', views.TournamentViewSet, basename='tournament')

urlpatterns = [
    path('', include(router.urls)),
]
```

---

## 4. Testing Standards

### 4.1 Test Organization

```
tests/
├── unit/
│   ├── test_models.py
│   ├── test_services.py
│   └── test_utils.py
├── integration/
│   ├── test_registration_flow.py
│   └── test_payment_flow.py
├── functional/
│   ├── test_tournament_lifecycle.py
│   └── test_bracket_generation.py
└── fixtures/
    ├── factories.py
    └── sample_data.py
```

### 4.2 Test Naming

```python
# test_tournament_service.py

import pytest
from apps.tournaments.services import TournamentService


class TestTournamentService:
    """Tests for TournamentService."""
    
    def test_create_tournament_with_valid_data_creates_tournament(
        self, user, valid_tournament_data
    ):
        """Test that create_tournament creates tournament with valid data."""
        tournament = TournamentService.create_tournament(
            organizer=user,
            data=valid_tournament_data
        )
        
        assert tournament.id is not None
        assert tournament.organizer == user
        assert tournament.name == valid_tournament_data['name']
    
    def test_create_tournament_with_invalid_dates_raises_error(
        self, user, invalid_date_data
    ):
        """Test that create_tournament raises error for invalid dates."""
        with pytest.raises(ValidationError):
            TournamentService.create_tournament(
                organizer=user,
                data=invalid_date_data
            )
```

### 4.3 Fixtures

```python
# conftest.py

import pytest
from django.contrib.auth import get_user_model
from apps.tournaments.tests.factories import TournamentFactory

User = get_user_model()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def tournament(user):
    """Create a test tournament."""
    return TournamentFactory(organizer=user)


@pytest.fixture
def valid_tournament_data():
    """Return valid tournament creation data."""
    return {
        'name': 'Test Tournament',
        'description': 'Test description',
        'game': 1,
        'start_date': '2025-12-01T10:00:00Z',
        'end_date': '2025-12-01T18:00:00Z',
    }
```

### 4.4 Factory Pattern

```python
# apps/tournaments/tests/factories.py

import factory
from factory.django import DjangoModelFactory
from apps.tournaments.models import Tournament


class TournamentFactory(DjangoModelFactory):
    """Factory for creating test tournaments."""
    
    class Meta:
        model = Tournament
    
    name = factory.Sequence(lambda n: f'Tournament {n}')
    description = factory.Faker('paragraph')
    organizer = factory.SubFactory('apps.accounts.tests.factories.UserFactory')
    game = factory.SubFactory('apps.tournaments.tests.factories.GameFactory')
    start_date = factory.Faker('future_datetime', end_date='+30d')
    end_date = factory.Faker('future_datetime', end_date='+31d')
    status = 'draft'
```

---

## 5. Frontend Standards

### 5.1 Template Structure

```html
<!-- templates/tournaments/detail.html -->
{% extends "base.html" %}
{% load static %}
{% load tournament_tags %}

{% block title %}{{ tournament.name }} - DeltaCrown{% endblock %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <!-- Header -->
    <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900">
            {{ tournament.name }}
        </h1>
        <p class="text-gray-600 mt-2">
            {{ tournament.description }}
        </p>
    </div>
    
    <!-- Content with HTMX -->
    <div 
        hx-get="{% url 'tournaments:participants' tournament.id %}"
        hx-trigger="load"
        hx-swap="innerHTML"
        class="bg-white rounded-lg shadow p-6"
    >
        <div class="animate-pulse">Loading...</div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
    // Alpine.js component
    document.addEventListener('alpine:init', () => {
        Alpine.data('tournamentDetail', () => ({
            showModal: false,
            init() {
                // Initialization
            }
        }));
    });
</script>
{% endblock %}
```

### 5.2 CSS/Tailwind Usage

```html
<!-- Use Tailwind utility classes -->
<button class="
    px-4 py-2 
    bg-blue-600 hover:bg-blue-700 
    text-white font-semibold 
    rounded-lg shadow
    transition duration-150 ease-in-out
    focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
">
    Register Now
</button>

<!-- For repeated patterns, create components -->
<!-- templates/components/button.html -->
<button class="btn btn-primary {{ extra_classes }}">
    {{ text }}
</button>
```

### 5.3 JavaScript Standards

```javascript
// Use Alpine.js for interactivity
<div x-data="{ 
    open: false,
    loading: false,
    async handleSubmit() {
        this.loading = true;
        try {
            const response = await fetch('/api/v1/register/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.formData)
            });
            if (response.ok) {
                this.open = false;
            }
        } finally {
            this.loading = false;
        }
    }
}">
    <button @click="open = true">Open Modal</button>
    
    <div x-show="open" x-cloak>
        <!-- Modal content -->
    </div>
</div>
```

---

## 6. Database Standards

### 6.1 Migration Guidelines

```python
# Always review generated migrations
# apps/tournaments/migrations/0001_initial.py

from django.db import migrations, models


class Migration(migrations.Migration):
    
    dependencies = [
        ('accounts', '0001_initial'),
    ]
    
    operations = [
        migrations.CreateModel(
            name='Tournament',
            fields=[
                ('id', models.UUIDField(primary_key=True)),
                ('name', models.CharField(max_length=200)),
                # ...
            ],
            options={
                'db_table': 'tournaments',
                'indexes': [
                    models.Index(fields=['status', '-created_at']),
                ],
            },
        ),
    ]
```

### 6.2 Query Optimization

```python
# Always use select_related for ForeignKey
tournaments = Tournament.objects.select_related(
    'organizer',
    'game'
).filter(status='published')

# Use prefetch_related for Many-to-Many
tournaments = Tournament.objects.prefetch_related(
    'participants',
    'participants__team'
).all()

# Use only() to limit fields
tournaments = Tournament.objects.only(
    'id', 'name', 'status'
).filter(status='published')

# Use defer() to exclude fields
tournaments = Tournament.objects.defer(
    'description'
).all()
```

---

## 7. Security Standards

### 7.1 Input Validation

```python
# Always validate and sanitize user input
from django.core.exceptions import ValidationError

def validate_tournament_name(name: str) -> str:
    """Validate and sanitize tournament name."""
    if len(name) < 3:
        raise ValidationError("Name must be at least 3 characters")
    if len(name) > 200:
        raise ValidationError("Name must be less than 200 characters")
    # Remove potentially dangerous characters
    return name.strip()
```

### 7.2 Permission Checks

```python
# Always check permissions before actions
from django.core.exceptions import PermissionDenied

def publish_tournament(tournament: Tournament, user: User) -> None:
    """Publish tournament."""
    if tournament.organizer != user:
        raise PermissionDenied("Only organizer can publish tournament")
    
    tournament.status = 'published'
    tournament.save()
```

### 7.3 SQL Injection Prevention

```python
# NEVER use string interpolation for queries
# BAD - SQL injection vulnerability
Tournament.objects.raw(f"SELECT * FROM tournaments WHERE name = '{name}'")

# GOOD - Use parameterized queries
Tournament.objects.raw("SELECT * FROM tournaments WHERE name = %s", [name])

# BEST - Use ORM
Tournament.objects.filter(name=name)
```

---

## 8. Documentation Standards

### 8.1 Code Comments

```python
# Single-line comments for simple explanations
participants_count = tournament.participants.count()  # Cache count

# Multi-line comments for complex logic
"""
Calculate tournament ranking using modified Swiss system:
1. Points from wins (3 points per win)
2. Tie-breaker: total match score differential
3. Secondary tie-breaker: head-to-head record
"""
```

### 8.2 README Structure

```markdown
# Feature Name

## Overview
Brief description of the feature.

## Installation
Steps to install dependencies.

## Usage
Example code showing how to use.

## API Reference
List of available methods with parameters.

## Testing
How to run tests.

## Contributing
Guidelines for contributing.
```

---

## 9. Error Handling

### 9.1 Exception Handling

```python
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def create_tournament(data: dict) -> Optional[Tournament]:
    """Create tournament with proper error handling."""
    try:
        tournament = TournamentService.create_tournament(data)
        logger.info(
            "Tournament created successfully",
            extra={
                'tournament_id': tournament.id,
                'organizer_id': data['organizer'].id
            }
        )
        return tournament
        
    except ValidationError as e:
        logger.warning(
            "Tournament validation failed",
            extra={'errors': e.message_dict}
        )
        raise
        
    except Exception as e:
        logger.error(
            "Unexpected error creating tournament",
            extra={'error': str(e)},
            exc_info=True
        )
        raise
```

### 9.2 User-Facing Errors

```python
from django.contrib import messages
from django.shortcuts import redirect

def tournament_create_view(request):
    """View with user-friendly error messages."""
    try:
        tournament = TournamentService.create_tournament(
            organizer=request.user,
            data=form.cleaned_data
        )
        messages.success(request, f"Tournament '{tournament.name}' created successfully!")
        return redirect('tournaments:detail', pk=tournament.id)
        
    except ValidationError as e:
        for field, errors in e.message_dict.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
        return redirect('tournaments:create')
```

---

## 10. Checklist Before Commit

### Code Quality
- [ ] Code follows PEP 8
- [ ] All functions have type hints
- [ ] All functions have docstrings
- [ ] No linting errors (flake8)
- [ ] Code formatted with Black
- [ ] Imports sorted with isort

### Testing
- [ ] Unit tests written
- [ ] Integration tests added (if needed)
- [ ] All tests passing
- [ ] Coverage >80% for changed code

### Security
- [ ] Input validation implemented
- [ ] Permission checks added
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities

### Documentation
- [ ] Code comments added
- [ ] README updated (if needed)
- [ ] API docs updated (if needed)
- [ ] Migration notes documented

### Performance
- [ ] No N+1 queries
- [ ] Appropriate indexes added
- [ ] Caching considered
- [ ] Database queries optimized

---

## Summary

Follow these standards for:
✅ Consistent codebase  
✅ Easier maintenance  
✅ Better collaboration  
✅ Higher quality  

**Questions?** Ask in #deltacrown-dev Slack channel

---

**Version History:**
- v1.0 (Nov 7, 2025) - Initial technical standards document

