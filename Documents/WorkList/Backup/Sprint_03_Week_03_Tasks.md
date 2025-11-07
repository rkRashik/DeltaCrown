# Sprint 3 - Week 3: Tournament Engine Backend

**Sprint Goal:** Implement core tournament backend (models, APIs, validation)  
**Duration:** Week 3 (5 days)  
**Story Points:** 50  
**Team:** Backend (3), Frontend (1), QA (1), DevOps (1)  
**Linked Epic:** Epic 2 - Tournament Engine (see `00_BACKLOG_OVERVIEW.md`)

---

## 📋 Task Cards - Backend Track - Core (30 points)

### **BE-006: Tournament Model & Database Schema**

**Type:** Story  
**Priority:** Critical (P0)  
**Story Points:** 8  
**Assignee:** Backend Dev 1  
**Sprint:** Sprint 3  
**Epic:** Epic 2 - Tournament Engine

**Description:**
Design and implement comprehensive Tournament model with all fields, relationships, and constraints. Include game-agnostic architecture supporting eFootball, Valorant, and future games. Implement status workflow (DRAFT → PUBLISHED → ONGOING → COMPLETED → CANCELLED).

**Acceptance Criteria:**
- [ ] Tournament model created in `apps/tournaments/models.py`
- [ ] **Core Fields:**
  - `id` (UUID, primary key)
  - `title` (CharField, max 200, indexed)
  - `slug` (SlugField, unique, auto-generated from title)
  - `description` (TextField)
  - `organizer` (ForeignKey to User, on_delete=CASCADE)
  - `game` (ForeignKey to GameConfig, on_delete=PROTECT)
  - `status` (CharField, choices: DRAFT, PUBLISHED, ONGOING, COMPLETED, CANCELLED)
  - `format` (CharField, choices: SINGLE_ELIMINATION, DOUBLE_ELIMINATION, SWISS, ROUND_ROBIN)
  - `team_size` (IntegerField, 1-10 players per team)
  - `max_teams` (IntegerField, must be power of 2 for elimination formats)
  - `entry_fee` (DecimalField, max_digits=10, decimal_places=2, default=0)
  - `prize_pool` (DecimalField, max_digits=12, decimal_places=2)
  - `registration_start` (DateTimeField)
  - `registration_end` (DateTimeField)
  - `tournament_start` (DateTimeField)
  - `tournament_end` (DateTimeField, nullable)
  - `check_in_start` (DateTimeField)
  - `check_in_end` (DateTimeField)
  - `rules_text` (TextField, markdown support)
  - `logo` (ImageField, upload_to='tournaments/logos/', nullable)
  - `banner` (ImageField, upload_to='tournaments/banners/', nullable)
  - `featured` (BooleanField, default=False, for homepage carousel)
  - `visibility` (CharField, choices: PUBLIC, PRIVATE, UNLISTED)
  - `created_at` (DateTimeField, auto_now_add)
  - `updated_at` (DateTimeField, auto_now)
- [ ] **Validation Methods:**
  - `clean()`: Validate registration_end < tournament_start
  - `clean()`: Validate check_in_end < tournament_start
  - `clean()`: Validate max_teams is power of 2 for elimination formats
  - `clean()`: Validate team_size matches game requirements
- [ ] **Manager Methods:**
  - `TournamentManager.published()`: Returns published tournaments
  - `TournamentManager.upcoming()`: Returns future tournaments
  - `TournamentManager.ongoing()`: Returns active tournaments
  - `TournamentManager.by_game(game_slug)`: Filter by game
- [ ] **Instance Methods:**
  - `get_absolute_url()`: Returns `/tournaments/<slug>/`
  - `can_register()`: Returns True if registration open
  - `is_full()`: Returns True if max_teams reached
  - `get_status_display_color()`: Returns Tailwind color class
- [ ] Database migration created and applied
- [ ] Model registered in admin with custom ModelAdmin
- [ ] Meta options: `ordering = ['-created_at']`, `indexes` on slug, status, game

**Dependencies:**
- BE-002 (PostgreSQL setup)
- BE-004 (User model)

**Technical Notes:**
- Use UUID for `id` to prevent enumeration attacks
- SlugField auto-populated from title using `django.utils.text.slugify`
- ImageField requires Pillow library and media file configuration
- Status transitions enforced via model methods (no direct status changes)
- Reference: PROPOSAL_PART_2.md Section 4.1 (Tournament Engine), PROPOSAL_PART_3.md Section 3.2 (Tournament Model)

**Files to Create/Modify:**
- `apps/tournaments/models.py` (create Tournament model)
- `apps/tournaments/migrations/0001_initial.py` (auto-generated)
- `apps/tournaments/admin.py` (register TournamentAdmin)
- `apps/tournaments/managers.py` (create TournamentManager)
- `deltacrown/settings.py` (add MEDIA_URL, MEDIA_ROOT)

**Tournament Model Example:**
```python
from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError
import uuid

class TournamentManager(models.Manager):
    def published(self):
        return self.filter(status='PUBLISHED')
    
    def upcoming(self):
        from django.utils import timezone
        return self.published().filter(tournament_start__gt=timezone.now())
    
    def ongoing(self):
        from django.utils import timezone
        now = timezone.now()
        return self.filter(status='ONGOING', tournament_start__lte=now)

class Tournament(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PUBLISHED', 'Published'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    FORMAT_CHOICES = [
        ('SINGLE_ELIMINATION', 'Single Elimination'),
        ('DOUBLE_ELIMINATION', 'Double Elimination'),
        ('SWISS', 'Swiss'),
        ('ROUND_ROBIN', 'Round Robin'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()
    organizer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='organized_tournaments')
    game = models.ForeignKey('game_configs.GameConfig', on_delete=models.PROTECT, related_name='tournaments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT', db_index=True)
    format = models.CharField(max_length=30, choices=FORMAT_CHOICES)
    team_size = models.IntegerField(default=1)
    max_teams = models.IntegerField()
    entry_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    prize_pool = models.DecimalField(max_digits=12, decimal_places=2)
    registration_start = models.DateTimeField()
    registration_end = models.DateTimeField()
    tournament_start = models.DateTimeField()
    tournament_end = models.DateTimeField(null=True, blank=True)
    check_in_start = models.DateTimeField()
    check_in_end = models.DateTimeField()
    rules_text = models.TextField(blank=True)
    logo = models.ImageField(upload_to='tournaments/logos/', null=True, blank=True)
    banner = models.ImageField(upload_to='tournaments/banners/', null=True, blank=True)
    featured = models.BooleanField(default=False)
    visibility = models.CharField(max_length=20, choices=[('PUBLIC', 'Public'), ('PRIVATE', 'Private'), ('UNLISTED', 'Unlisted')], default='PUBLIC')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now)
    
    objects = TournamentManager()
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status']),
            models.Index(fields=['game', 'status']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def clean(self):
        if self.registration_end >= self.tournament_start:
            raise ValidationError('Registration must end before tournament starts')
        if self.check_in_end >= self.tournament_start:
            raise ValidationError('Check-in must end before tournament starts')
        if self.format in ['SINGLE_ELIMINATION', 'DOUBLE_ELIMINATION']:
            if not (self.max_teams & (self.max_teams - 1) == 0):
                raise ValidationError('Max teams must be power of 2 for elimination formats')
    
    def can_register(self):
        from django.utils import timezone
        now = timezone.now()
        return (self.status == 'PUBLISHED' and 
                self.registration_start <= now <= self.registration_end and
                not self.is_full())
    
    def is_full(self):
        return self.registrations.filter(status='CONFIRMED').count() >= self.max_teams
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('tournaments:detail', kwargs={'slug': self.slug})
    
    def get_status_display_color(self):
        colors = {
            'DRAFT': 'gray',
            'PUBLISHED': 'blue',
            'ONGOING': 'green',
            'COMPLETED': 'purple',
            'CANCELLED': 'red',
        }
        return colors.get(self.status, 'gray')
    
    def __str__(self):
        return self.title
```

**Testing:**
- Create tournament via Django shell → verify all fields saved
- Test slug auto-generation: "My Tournament" → "my-tournament"
- Test validation: registration_end >= tournament_start → ValidationError
- Test max_teams validation: 7 teams + SINGLE_ELIMINATION → ValidationError
- Test manager methods: `Tournament.objects.published()` returns only published
- Test `can_register()`: Returns True if registration window open and not full
- Run migration: `python manage.py makemigrations tournaments`
- Apply migration: `python manage.py migrate tournaments`

---

### **BE-007: Game Configuration Model**

**Type:** Story  
**Priority:** Critical (P0)  
**Story Points:** 5  
**Assignee:** Backend Dev 2  
**Sprint:** Sprint 3  
**Epic:** Epic 2 - Tournament Engine

**Description:**
Create GameConfig model to store game-specific configuration (eFootball, Valorant, future games). Define platform options, team size constraints, match settings, and validation rules per game.

**Acceptance Criteria:**
- [ ] GameConfig model created in `apps/game_configs/models.py`
- [ ] **Core Fields:**
  - `id` (UUID, primary key)
  - `name` (CharField, max 100, unique) - e.g., "eFootball 2024"
  - `slug` (SlugField, unique) - e.g., "efootball-2024"
  - `game_type` (CharField, choices: EFOOTBALL, VALORANT, FIFA, CSGO, LOL, DOTA2)
  - `icon` (ImageField, upload_to='games/icons/')
  - `banner` (ImageField, upload_to='games/banners/')
  - `description` (TextField)
  - `is_active` (BooleanField, default=True)
  - `min_team_size` (IntegerField, default=1)
  - `max_team_size` (IntegerField, default=5)
  - `platforms` (JSONField) - e.g., ["PC", "PS5", "Xbox"]
  - `match_settings` (JSONField) - e.g., {"half_length": 6, "difficulty": "Professional"}
  - `validation_rules` (JSONField) - e.g., {"require_game_id": true, "min_level": 10}
  - `created_at` (DateTimeField, auto_now_add)
  - `updated_at` (DateTimeField, auto_now)
- [ ] **Manager Methods:**
  - `GameConfigManager.active()`: Returns active games
  - `GameConfigManager.by_type(game_type)`: Filter by game type
- [ ] **Instance Methods:**
  - `get_platform_choices()`: Returns platform options as list
  - `validate_team_size(size)`: Returns True if valid for this game
  - `get_icon_url()`: Returns absolute URL for icon
- [ ] Database migration created and applied
- [ ] Model registered in admin
- [ ] Seed data created: eFootball 2024, Valorant

**Dependencies:**
- BE-002 (PostgreSQL with JSONField support)

**Technical Notes:**
- Use JSONField for flexible game-specific settings (no schema changes for new games)
- Platforms stored as JSON array: `["PC", "PS5", "Xbox Series X/S"]`
- Match settings vary by game (eFootball: half_length, Valorant: rounds_to_win)
- Reference: PROPOSAL_PART_2.md Section 4.2 (Game Configuration), PROPOSAL_PART_3.md Section 3.9 (GameConfig Model)

**Files to Create/Modify:**
- `apps/game_configs/models.py` (create GameConfig model)
- `apps/game_configs/migrations/0001_initial.py` (auto-generated)
- `apps/game_configs/admin.py` (register GameConfigAdmin)
- `apps/game_configs/fixtures/initial_games.json` (seed data)
- `apps/game_configs/management/commands/load_games.py` (seed command)

**GameConfig Model Example:**
```python
from django.db import models
from django.utils.text import slugify
import uuid

class GameConfigManager(models.Manager):
    def active(self):
        return self.filter(is_active=True)
    
    def by_type(self, game_type):
        return self.filter(game_type=game_type, is_active=True)

class GameConfig(models.Model):
    GAME_TYPE_CHOICES = [
        ('EFOOTBALL', 'eFootball'),
        ('VALORANT', 'Valorant'),
        ('FIFA', 'FIFA'),
        ('CSGO', 'Counter-Strike: GO'),
        ('LOL', 'League of Legends'),
        ('DOTA2', 'Dota 2'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    game_type = models.CharField(max_length=20, choices=GAME_TYPE_CHOICES, db_index=True)
    icon = models.ImageField(upload_to='games/icons/')
    banner = models.ImageField(upload_to='games/banners/', null=True, blank=True)
    description = models.TextField()
    is_active = models.BooleanField(default=True, db_index=True)
    min_team_size = models.IntegerField(default=1)
    max_team_size = models.IntegerField(default=5)
    platforms = models.JSONField(default=list)
    match_settings = models.JSONField(default=dict)
    validation_rules = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now)
    
    objects = GameConfigManager()
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Game Configuration'
        verbose_name_plural = 'Game Configurations'
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_platform_choices(self):
        return self.platforms if isinstance(self.platforms, list) else []
    
    def validate_team_size(self, size):
        return self.min_team_size <= size <= self.max_team_size
    
    def get_icon_url(self):
        return self.icon.url if self.icon else '/static/img/game-placeholder.png'
    
    def __str__(self):
        return self.name
```

**Seed Data Example (initial_games.json):**
```json
[
  {
    "model": "game_configs.gameconfig",
    "pk": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "fields": {
      "name": "eFootball 2024",
      "slug": "efootball-2024",
      "game_type": "EFOOTBALL",
      "description": "The latest evolution of PES, offering realistic football simulation.",
      "is_active": true,
      "min_team_size": 1,
      "max_team_size": 11,
      "platforms": ["PC", "PS5", "PS4", "Xbox Series X/S", "Xbox One"],
      "match_settings": {
        "half_length": 6,
        "difficulty": "Professional",
        "stamina": true,
        "injuries": false
      },
      "validation_rules": {
        "require_game_id": true,
        "min_account_level": 5
      }
    }
  },
  {
    "model": "game_configs.gameconfig",
    "pk": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "fields": {
      "name": "Valorant",
      "slug": "valorant",
      "game_type": "VALORANT",
      "description": "5v5 character-based tactical FPS by Riot Games.",
      "is_active": true,
      "min_team_size": 1,
      "max_team_size": 5,
      "platforms": ["PC"],
      "match_settings": {
        "rounds_to_win": 13,
        "overtime": true,
        "tournament_mode": true
      },
      "validation_rules": {
        "require_riot_id": true,
        "min_rank": "Silver"
      }
    }
  }
]
```

**Testing:**
- Load seed data: `python manage.py loaddata initial_games`
- Query active games: `GameConfig.objects.active()` returns 2 games
- Test team size validation: `efootball.validate_team_size(11)` → True
- Test platform choices: `valorant.get_platform_choices()` → ["PC"]
- Test slug generation: "eFootball 2024" → "efootball-2024"

---

### **BE-008: Tournament API Endpoints (CRUD)**

**Type:** Story  
**Priority:** Critical (P0)  
**Story Points:** 8  
**Assignee:** Backend Dev 1  
**Sprint:** Sprint 3  
**Epic:** Epic 2 - Tournament Engine

**Description:**
Implement RESTful API endpoints for tournament CRUD operations using Django REST Framework. Include list, retrieve, create, update, delete, and custom actions (publish, cancel). Implement filtering, search, pagination, and permissions.

**Acceptance Criteria:**
- [ ] **Endpoints Implemented:**
  - `GET /api/tournaments/` - List tournaments (paginated, 20 per page)
  - `GET /api/tournaments/<slug>/` - Retrieve tournament detail
  - `POST /api/tournaments/` - Create tournament (organizers only)
  - `PUT/PATCH /api/tournaments/<slug>/` - Update tournament (organizer/admin only)
  - `DELETE /api/tournaments/<slug>/` - Delete tournament (organizer/admin only)
  - `POST /api/tournaments/<slug>/publish/` - Publish tournament (custom action)
  - `POST /api/tournaments/<slug>/cancel/` - Cancel tournament (custom action)
- [ ] **Serializers:**
  - `TournamentListSerializer`: Lightweight (id, title, slug, game, status, prize_pool, max_teams, registration_end, logo)
  - `TournamentDetailSerializer`: Full fields + nested game + organizer
  - `TournamentCreateSerializer`: Validation + auto-set organizer
  - `TournamentUpdateSerializer`: Partial updates allowed
- [ ] **Filtering:** By game, status, organizer, featured (use django-filter)
- [ ] **Search:** By title, description (use DRF SearchFilter)
- [ ] **Ordering:** By created_at, tournament_start, prize_pool
- [ ] **Permissions:**
  - List/Retrieve: Public (read-only)
  - Create: Authenticated organizers only
  - Update/Delete: Owner or admin only
  - Publish/Cancel: Owner or admin only
- [ ] **Validation:**
  - Prevent publishing if required fields missing
  - Prevent deletion if tournament has confirmed registrations
  - Prevent status changes if invalid workflow (e.g., COMPLETED → DRAFT)
- [ ] API documentation generated (OpenAPI/Swagger)

**Dependencies:**
- BE-006 (Tournament model)
- BE-005 (JWT authentication)

**Technical Notes:**
- Use `ModelViewSet` for standard CRUD
- Custom actions use `@action(detail=True, methods=['post'])`
- Permissions: `IsAuthenticatedOrReadOnly` + custom `IsOrganizerOrAdmin`
- Reference: PROPOSAL_PART_2.md Section 4.3 (Tournament API)

**Files to Create/Modify:**
- `apps/tournaments/serializers.py` (create serializers)
- `apps/tournaments/views.py` (create TournamentViewSet)
- `apps/tournaments/permissions.py` (create IsOrganizerOrAdmin)
- `apps/tournaments/filters.py` (create TournamentFilter)
- `apps/tournaments/urls.py` (router registration)
- `deltacrown/urls.py` (include tournaments API)

**TournamentViewSet Example:**
```python
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from .models import Tournament
from .serializers import TournamentListSerializer, TournamentDetailSerializer
from .permissions import IsOrganizerOrAdmin
from .filters import TournamentFilter

class TournamentViewSet(viewsets.ModelViewSet):
    queryset = Tournament.objects.select_related('game', 'organizer').all()
    permission_classes = [IsAuthenticatedOrReadOnly, IsOrganizerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TournamentFilter
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'tournament_start', 'prize_pool']
    ordering = ['-created_at']
    lookup_field = 'slug'
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TournamentListSerializer
        return TournamentDetailSerializer
    
    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsOrganizerOrAdmin])
    def publish(self, request, slug=None):
        tournament = self.get_object()
        if tournament.status != 'DRAFT':
            return Response({'error': 'Only draft tournaments can be published'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        tournament.status = 'PUBLISHED'
        tournament.save()
        return Response({'status': 'Tournament published'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsOrganizerOrAdmin])
    def cancel(self, request, slug=None):
        tournament = self.get_object()
        if tournament.status in ['COMPLETED', 'CANCELLED']:
            return Response({'error': 'Cannot cancel completed/cancelled tournament'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        tournament.status = 'CANCELLED'
        tournament.save()
        return Response({'status': 'Tournament cancelled'})
```

**Permission Example:**
```python
from rest_framework import permissions

class IsOrganizerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.organizer == request.user or request.user.is_staff
```

**Testing:**
- List tournaments: `curl http://localhost:8000/api/tournaments/`
- Filter by game: `curl http://localhost:8000/api/tournaments/?game=efootball-2024`
- Search: `curl http://localhost:8000/api/tournaments/?search=valorant`
- Create tournament (authenticated):
  ```bash
  curl -X POST http://localhost:8000/api/tournaments/ \
    -H "Authorization: Bearer <token>" \
    -H "Content-Type: application/json" \
    -d '{
      "title": "Summer Valorant Cup",
      "game": "valorant",
      "format": "SINGLE_ELIMINATION",
      "max_teams": 16,
      "prize_pool": 1000,
      "registration_start": "2025-06-01T00:00:00Z",
      "registration_end": "2025-06-15T23:59:59Z",
      "tournament_start": "2025-06-20T10:00:00Z"
    }'
  ```
- Publish tournament: `curl -X POST http://localhost:8000/api/tournaments/summer-valorant-cup/publish/`
- Verify permissions: Unauthenticated user cannot create/update/delete

---

### **BE-009: Game Configuration API**

**Type:** Story  
**Priority:** High (P1)  
**Story Points:** 5  
**Assignee:** Backend Dev 2  
**Sprint:** Sprint 3  
**Epic:** Epic 2 - Tournament Engine

**Description:**
Create read-only API endpoints for GameConfig. Provide list and detail views with platform choices, match settings, and validation rules for frontend tournament creation wizard.

**Acceptance Criteria:**
- [ ] **Endpoints Implemented:**
  - `GET /api/games/` - List all active games
  - `GET /api/games/<slug>/` - Retrieve game config detail
- [ ] **Serializer:**
  - `GameConfigSerializer`: All fields serialized
  - Computed field: `tournament_count` (number of tournaments using this game)
  - Computed field: `platform_choices` (formatted for dropdowns)
- [ ] **Filtering:** By game_type, is_active
- [ ] **Permissions:** Public read-only (no authentication required)
- [ ] **Response Format:**
  ```json
  {
    "id": "uuid",
    "name": "eFootball 2024",
    "slug": "efootball-2024",
    "game_type": "EFOOTBALL",
    "icon": "https://cdn.example.com/games/icons/efootball.png",
    "min_team_size": 1,
    "max_team_size": 11,
    "platforms": ["PC", "PS5", "Xbox"],
    "platform_choices": [
      {"value": "PC", "label": "PC"},
      {"value": "PS5", "label": "PlayStation 5"}
    ],
    "match_settings": {"half_length": 6},
    "tournament_count": 42
  }
  ```
- [ ] Caching: Cache list response for 1 hour (games rarely change)
- [ ] API documentation updated

**Dependencies:**
- BE-007 (GameConfig model)

**Technical Notes:**
- Use `ReadOnlyModelViewSet` (no create/update/delete)
- Cache using `@method_decorator(cache_page(3600))`
- Annotate queryset with `tournament_count` using `Count('tournaments')`
- Reference: PROPOSAL_PART_2.md Section 4.2 (Game Configuration API)

**Files to Create/Modify:**
- `apps/game_configs/serializers.py` (create GameConfigSerializer)
- `apps/game_configs/views.py` (create GameConfigViewSet)
- `apps/game_configs/urls.py` (router registration)
- `deltacrown/urls.py` (include game_configs API)

**GameConfigViewSet Example:**
```python
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.db.models import Count
from .models import GameConfig
from .serializers import GameConfigSerializer

class GameConfigViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GameConfig.objects.filter(is_active=True).annotate(
        tournament_count=Count('tournaments')
    )
    serializer_class = GameConfigSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    
    @method_decorator(cache_page(60 * 60))  # 1 hour cache
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
```

**GameConfigSerializer Example:**
```python
from rest_framework import serializers
from .models import GameConfig

class GameConfigSerializer(serializers.ModelSerializer):
    tournament_count = serializers.IntegerField(read_only=True)
    platform_choices = serializers.SerializerMethodField()
    
    class Meta:
        model = GameConfig
        fields = [
            'id', 'name', 'slug', 'game_type', 'icon', 'banner',
            'description', 'min_team_size', 'max_team_size', 'platforms',
            'platform_choices', 'match_settings', 'validation_rules',
            'tournament_count', 'created_at'
        ]
    
    def get_platform_choices(self, obj):
        return [{'value': p, 'label': p} for p in obj.get_platform_choices()]
```

**Testing:**
- List games: `curl http://localhost:8000/api/games/`
- Retrieve game: `curl http://localhost:8000/api/games/efootball-2024/`
- Verify tournament_count: Should show number of tournaments using game
- Verify caching: Second request should be faster (check response headers)
- Test unauthenticated access: Should work without token

---

### **BE-010: Tournament Validation Rules**

**Type:** Story  
**Priority:** Medium (P2)  
**Story Points:** 4  
**Assignee:** Backend Dev 3  
**Sprint:** Sprint 3  
**Epic:** Epic 2 - Tournament Engine

**Description:**
Implement comprehensive validation rules for tournament creation/updates. Validate date ranges, team size, max teams, prize pool, and game-specific requirements. Create reusable validator functions.

**Acceptance Criteria:**
- [ ] **Validation Functions Created:**
  - `validate_date_ranges(registration_start, registration_end, tournament_start, check_in_start, check_in_end)`: Ensures logical date progression
  - `validate_team_size(team_size, game_config)`: Checks against game min/max
  - `validate_max_teams(max_teams, format)`: Ensures power of 2 for elimination
  - `validate_prize_pool(prize_pool, entry_fee, max_teams)`: Ensures prize pool <= total entry fees (if paid tournament)
  - `validate_tournament_format(format, max_teams)`: Validates format constraints (Swiss needs even teams, etc.)
- [ ] **Model-level Validation:**
  - Override `Tournament.clean()` to call all validators
  - Raise `ValidationError` with user-friendly messages
- [ ] **Serializer-level Validation:**
  - Override `TournamentCreateSerializer.validate()` to call validators
  - Return 400 Bad Request with validation errors
- [ ] **Business Rules:**
  - Registration window must be at least 24 hours
  - Tournament must start within 90 days of creation
  - Check-in window must be at least 30 minutes
  - Max teams cannot exceed 256 (platform limit)
- [ ] Unit tests for all validators
- [ ] Documentation of validation rules in `docs/VALIDATION_RULES.md`

**Dependencies:**
- BE-006 (Tournament model)
- BE-007 (GameConfig model)
- BE-008 (Tournament API)

**Technical Notes:**
- Use `django.core.exceptions.ValidationError` for model validation
- Use `rest_framework.serializers.ValidationError` for API validation
- Validators should be reusable across admin, API, and frontend
- Reference: PROPOSAL_PART_2.md Section 4.4 (Validation Rules)

**Files to Create/Modify:**
- `apps/tournaments/validators.py` (new - all validation functions)
- `apps/tournaments/models.py` (update `Tournament.clean()`)
- `apps/tournaments/serializers.py` (update `TournamentCreateSerializer.validate()`)
- `apps/tournaments/tests/test_validators.py` (new - unit tests)
- `docs/VALIDATION_RULES.md` (new - documentation)

**Validators Example:**
```python
from django.core.exceptions import ValidationError
from datetime import timedelta

def validate_date_ranges(registration_start, registration_end, tournament_start, check_in_start, check_in_end):
    """Validate tournament date ranges"""
    errors = []
    
    if registration_end <= registration_start:
        errors.append('Registration end must be after registration start')
    
    if registration_end >= tournament_start:
        errors.append('Registration must end before tournament starts')
    
    if check_in_end >= tournament_start:
        errors.append('Check-in must end before tournament starts')
    
    if check_in_start >= check_in_end:
        errors.append('Check-in start must be before check-in end')
    
    # Business rule: registration window at least 24 hours
    if (registration_end - registration_start) < timedelta(hours=24):
        errors.append('Registration window must be at least 24 hours')
    
    # Business rule: check-in window at least 30 minutes
    if (check_in_end - check_in_start) < timedelta(minutes=30):
        errors.append('Check-in window must be at least 30 minutes')
    
    if errors:
        raise ValidationError(errors)

def validate_team_size(team_size, game_config):
    """Validate team size against game requirements"""
    if not game_config.validate_team_size(team_size):
        raise ValidationError(
            f'Team size must be between {game_config.min_team_size} and {game_config.max_team_size} for {game_config.name}'
        )

def validate_max_teams(max_teams, format):
    """Validate max teams for tournament format"""
    if max_teams > 256:
        raise ValidationError('Maximum 256 teams allowed')
    
    if format in ['SINGLE_ELIMINATION', 'DOUBLE_ELIMINATION']:
        # Check if power of 2
        if not (max_teams > 0 and (max_teams & (max_teams - 1)) == 0):
            raise ValidationError(f'{format} format requires max_teams to be power of 2 (8, 16, 32, 64, etc.)')

def validate_prize_pool(prize_pool, entry_fee, max_teams):
    """Validate prize pool doesn't exceed total entry fees"""
    if entry_fee > 0:
        total_possible = entry_fee * max_teams
        if prize_pool > total_possible:
            raise ValidationError(
                f'Prize pool (${prize_pool}) exceeds total entry fees (${total_possible})'
            )

def validate_tournament_format(format, max_teams):
    """Validate format-specific constraints"""
    if format == 'SWISS':
        if max_teams < 4:
            raise ValidationError('Swiss format requires at least 4 teams')
    elif format == 'ROUND_ROBIN':
        if max_teams > 16:
            raise ValidationError('Round Robin format supports maximum 16 teams')
```

**Updated Tournament.clean():**
```python
def clean(self):
    from .validators import (
        validate_date_ranges, validate_team_size, validate_max_teams,
        validate_prize_pool, validate_tournament_format
    )
    
    # Validate date ranges
    validate_date_ranges(
        self.registration_start, self.registration_end,
        self.tournament_start, self.check_in_start, self.check_in_end
    )
    
    # Validate team size
    if self.game:
        validate_team_size(self.team_size, self.game)
    
    # Validate max teams
    validate_max_teams(self.max_teams, self.format)
    
    # Validate prize pool
    validate_prize_pool(self.prize_pool, self.entry_fee, self.max_teams)
    
    # Validate format
    validate_tournament_format(self.format, self.max_teams)
```

**Testing:**
- Test date validation: registration_end >= tournament_start → ValidationError
- Test team size: team_size=12, game=Valorant (max 5) → ValidationError
- Test max teams: max_teams=15, format=SINGLE_ELIMINATION → ValidationError (not power of 2)
- Test prize pool: entry_fee=10, max_teams=16, prize_pool=200 → ValidationError (exceeds 160)
- Test format: format=ROUND_ROBIN, max_teams=20 → ValidationError (max 16)
- Run unit tests: `pytest apps/tournaments/tests/test_validators.py`

---

## 📋 Task Cards - Backend Track - Teams (15 points)

### **BE-011: Team Model & Database Schema**

**Type:** Story  
**Priority:** Critical (P0)  
**Story Points:** 6  
**Assignee:** Backend Dev 2  
**Sprint:** Sprint 3  
**Epic:** Epic 2 - Tournament Engine

**Description:**
Create Team model representing player groups for tournament participation. Support captain assignment, team member management, verification status, and tournament-specific teams. Handle both permanent teams and ad-hoc tournament teams.

**Acceptance Criteria:**
- [ ] Team model created in `apps/teams/models.py`
- [ ] **Core Fields:**
  - `id` (UUID, primary key)
  - `name` (CharField, max 100)
  - `slug` (SlugField, unique)
  - `tag` (CharField, max 10, unique) - e.g., "FNC", "G2"
  - `captain` (ForeignKey to User, on_delete=SET_NULL, nullable)
  - `description` (TextField, blank=True)
  - `logo` (ImageField, upload_to='teams/logos/', nullable)
  - `is_verified` (BooleanField, default=False) - for official/sponsored teams
  - `is_active` (BooleanField, default=True)
  - `country` (CountryField, using django-countries)
  - `website` (URLField, blank=True)
  - `twitter` (CharField, max 50, blank=True)
  - `discord` (CharField, max 100, blank=True)
  - `created_at` (DateTimeField, auto_now_add)
  - `updated_at` (DateTimeField, auto_now)
- [ ] **Related Models:**
  - `TeamMember` model (Team-User many-to-many through model):
    - `team` (ForeignKey to Team)
    - `player` (ForeignKey to User)
    - `role` (CharField, choices: CAPTAIN, PLAYER, SUBSTITUTE)
    - `joined_at` (DateTimeField, auto_now_add)
    - `is_active` (BooleanField, default=True)
- [ ] **Manager Methods:**
  - `TeamManager.verified()`: Returns verified teams
  - `TeamManager.by_captain(user)`: Filter by captain
- [ ] **Instance Methods:**
  - `get_absolute_url()`: Returns `/teams/<slug>/`
  - `get_members()`: Returns active members
  - `get_member_count()`: Returns count of active members
  - `has_member(user)`: Check if user is member
  - `can_join_tournament(tournament)`: Validates team size matches tournament requirements
- [ ] Unique constraint: (name, tag) combination unique
- [ ] Database migrations created and applied
- [ ] Model registered in admin with inline TeamMember

**Dependencies:**
- BE-004 (User model)
- BE-002 (PostgreSQL)

**Technical Notes:**
- Use `django-countries` for country field (ISO country codes)
- Team tag used for display (e.g., "Team Liquid [TL]")
- Captain can manage team roster, but admin can override
- TeamMember through model allows tracking join date and role changes
- Reference: PROPOSAL_PART_3.md Section 3.3 (Team Model)

**Files to Create/Modify:**
- `apps/teams/models.py` (create Team, TeamMember)
- `apps/teams/migrations/0001_initial.py` (auto-generated)
- `apps/teams/admin.py` (register TeamAdmin with TeamMemberInline)
- `apps/teams/managers.py` (create TeamManager)

**Team Model Example:**
```python
from django.db import models
from django.utils.text import slugify
from django_countries.fields import CountryField
import uuid

class TeamManager(models.Manager):
    def verified(self):
        return self.filter(is_verified=True, is_active=True)
    
    def by_captain(self, user):
        return self.filter(captain=user, is_active=True)

class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    tag = models.CharField(max_length=10, unique=True, help_text="Team abbreviation (e.g., FNC, G2)")
    captain = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='captained_teams')
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='teams/logos/', null=True, blank=True)
    is_verified = models.BooleanField(default=False, help_text="Official/sponsored team")
    is_active = models.BooleanField(default=True, db_index=True)
    country = CountryField(blank=True)
    website = models.URLField(blank=True)
    twitter = models.CharField(max_length=50, blank=True)
    discord = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now)
    
    members = models.ManyToManyField('accounts.User', through='TeamMember', related_name='teams')
    
    objects = TeamManager()
    
    class Meta:
        ordering = ['-created_at']
        unique_together = [['name', 'tag']]
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_verified', 'is_active']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.name}-{self.tag}")
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('teams:detail', kwargs={'slug': self.slug})
    
    def get_members(self):
        return self.teammember_set.filter(is_active=True).select_related('player')
    
    def get_member_count(self):
        return self.get_members().count()
    
    def has_member(self, user):
        return self.members.filter(id=user.id, teammember__is_active=True).exists()
    
    def can_join_tournament(self, tournament):
        member_count = self.get_member_count()
        return member_count >= tournament.team_size
    
    def __str__(self):
        return f"{self.name} [{self.tag}]"

class TeamMember(models.Model):
    ROLE_CHOICES = [
        ('CAPTAIN', 'Captain'),
        ('PLAYER', 'Player'),
        ('SUBSTITUTE', 'Substitute'),
    ]
    
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    player = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='PLAYER')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = [['team', 'player']]
        ordering = ['-joined_at']
    
    def __str__(self):
        return f"{self.player.username} - {self.team.name} ({self.role})"
```

**Testing:**
- Create team via Django shell → verify all fields saved
- Add team members → verify many-to-many relationship
- Set captain → verify captain is also team member
- Test slug generation: "Team Liquid" + "TL" → "team-liquid-tl"
- Test `has_member()`: Returns True for active members
- Test `can_join_tournament()`: Returns True if team size sufficient
- Run migration: `python manage.py makemigrations teams && python manage.py migrate teams`

---

### **BE-012: Team API Endpoints**

**Type:** Story  
**Priority:** High (P1)  
**Story Points:** 5  
**Assignee:** Backend Dev 3  
**Sprint:** Sprint 3  
**Epic:** Epic 2 - Tournament Engine

**Description:**
Create RESTful API endpoints for team management. Support CRUD operations, member management (add/remove players), captain transfer, and team roster queries.

**Acceptance Criteria:**
- [ ] **Endpoints Implemented:**
  - `GET /api/teams/` - List teams (paginated, 20 per page)
  - `GET /api/teams/<slug>/` - Retrieve team detail
  - `POST /api/teams/` - Create team (authenticated users)
  - `PUT/PATCH /api/teams/<slug>/` - Update team (captain/admin only)
  - `DELETE /api/teams/<slug>/` - Delete team (captain/admin only)
  - `GET /api/teams/<slug>/members/` - List team members
  - `POST /api/teams/<slug>/members/` - Add member (captain/admin only)
  - `DELETE /api/teams/<slug>/members/<user_id>/` - Remove member (captain/admin only)
  - `POST /api/teams/<slug>/transfer-captain/` - Transfer captain (current captain only)
- [ ] **Serializers:**
  - `TeamListSerializer`: Lightweight (id, name, slug, tag, logo, member_count, is_verified)
  - `TeamDetailSerializer`: Full fields + nested members
  - `TeamMemberSerializer`: User info + role + joined_at
  - `TeamCreateSerializer`: Validation + auto-set creator as captain
- [ ] **Filtering:** By is_verified, country, captain
- [ ] **Search:** By name, tag
- [ ] **Permissions:**
  - List/Retrieve: Public
  - Create: Authenticated users
  - Update/Delete: Captain or admin
  - Member management: Captain or admin
- [ ] **Validation:**
  - Team name and tag must be unique
  - Cannot add duplicate members
  - Cannot remove captain (must transfer first)
  - Maximum 20 members per team
- [ ] API documentation updated

**Dependencies:**
- BE-011 (Team model)
- BE-005 (JWT authentication)

**Technical Notes:**
- Use `ModelViewSet` for standard CRUD
- Nested routes for member management
- Permissions: Custom `IsCaptainOrAdmin` permission class
- Reference: PROPOSAL_PART_2.md Section 4.5 (Team API)

**Files to Create/Modify:**
- `apps/teams/serializers.py` (create serializers)
- `apps/teams/views.py` (create TeamViewSet)
- `apps/teams/permissions.py` (create IsCaptainOrAdmin)
- `apps/teams/urls.py` (router registration)
- `deltacrown/urls.py` (include teams API)

**TeamViewSet Example:**
```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .models import Team, TeamMember
from .serializers import TeamListSerializer, TeamDetailSerializer, TeamMemberSerializer
from .permissions import IsCaptainOrAdmin

class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.select_related('captain').prefetch_related('members').filter(is_active=True)
    permission_classes = [IsAuthenticatedOrReadOnly, IsCaptainOrAdmin]
    lookup_field = 'slug'
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TeamListSerializer
        return TeamDetailSerializer
    
    def perform_create(self, serializer):
        team = serializer.save(captain=self.request.user)
        # Add creator as captain member
        TeamMember.objects.create(
            team=team,
            player=self.request.user,
            role='CAPTAIN'
        )
    
    @action(detail=True, methods=['get'])
    def members(self, request, slug=None):
        team = self.get_object()
        members = team.get_members()
        serializer = TeamMemberSerializer(members, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsCaptainOrAdmin])
    def add_member(self, request, slug=None):
        team = self.get_object()
        user_id = request.data.get('user_id')
        role = request.data.get('role', 'PLAYER')
        
        if team.get_member_count() >= 20:
            return Response({'error': 'Team is full (max 20 members)'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        if team.has_member(user_id):
            return Response({'error': 'User already in team'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        member = TeamMember.objects.create(
            team=team,
            player_id=user_id,
            role=role
        )
        serializer = TeamMemberSerializer(member)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['delete'], url_path='members/(?P<user_id>[^/.]+)', 
            permission_classes=[IsCaptainOrAdmin])
    def remove_member(self, request, slug=None, user_id=None):
        team = self.get_object()
        
        if str(team.captain_id) == user_id:
            return Response({'error': 'Cannot remove captain. Transfer captaincy first.'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        TeamMember.objects.filter(team=team, player_id=user_id).update(is_active=False)
        return Response({'status': 'Member removed'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsCaptainOrAdmin])
    def transfer_captain(self, request, slug=None):
        team = self.get_object()
        new_captain_id = request.data.get('new_captain_id')
        
        if not team.has_member(new_captain_id):
            return Response({'error': 'New captain must be team member'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Update old captain role to PLAYER
        TeamMember.objects.filter(team=team, player=team.captain).update(role='PLAYER')
        
        # Update new captain
        team.captain_id = new_captain_id
        team.save()
        TeamMember.objects.filter(team=team, player_id=new_captain_id).update(role='CAPTAIN')
        
        return Response({'status': 'Captain transferred'})
```

**IsCaptainOrAdmin Permission:**
```python
from rest_framework import permissions

class IsCaptainOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.captain == request.user or request.user.is_staff
```

**Testing:**
- List teams: `curl http://localhost:8000/api/teams/`
- Create team: `curl -X POST http://localhost:8000/api/teams/ -H "Authorization: Bearer <token>" -d '{"name":"Team Alpha","tag":"TA"}'`
- Get team members: `curl http://localhost:8000/api/teams/team-alpha-ta/members/`
- Add member: `curl -X POST http://localhost:8000/api/teams/team-alpha-ta/add_member/ -d '{"user_id":"user-uuid","role":"PLAYER"}'`
- Transfer captain: `curl -X POST http://localhost:8000/api/teams/team-alpha-ta/transfer_captain/ -d '{"new_captain_id":"user-uuid"}'`
- Verify permissions: Non-captain cannot update team

---

### **BE-013: Tournament-Team Registration Model**

**Type:** Story  
**Priority:** Critical (P0)  
**Story Points:** 4  
**Assignee:** Backend Dev 1  
**Sprint:** Sprint 3  
**Epic:** Epic 2 - Tournament Engine

**Description:**
Create TournamentRegistration model linking teams to tournaments. Track registration status (PENDING, CONFIRMED, CHECKED_IN, CANCELLED), payment status, check-in timestamps, and seed assignments.

**Acceptance Criteria:**
- [ ] TournamentRegistration model created in `apps/tournaments/models.py`
- [ ] **Core Fields:**
  - `id` (UUID, primary key)
  - `tournament` (ForeignKey to Tournament, on_delete=CASCADE)
  - `team` (ForeignKey to Team, on_delete=CASCADE)
  - `status` (CharField, choices: PENDING, CONFIRMED, CHECKED_IN, CANCELLED, DISQUALIFIED)
  - `payment_status` (CharField, choices: NOT_REQUIRED, PENDING, PAID, REFUNDED)
  - `payment_proof` (FileField, upload_to='registrations/payments/', nullable)
  - `registered_at` (DateTimeField, auto_now_add)
  - `confirmed_at` (DateTimeField, nullable)
  - `checked_in_at` (DateTimeField, nullable)
  - `seed` (IntegerField, nullable) - for bracket seeding
  - `notes` (TextField, blank=True) - admin notes
- [ ] **Validation:**
  - Unique constraint: (tournament, team)
  - Cannot register if tournament full
  - Cannot register if registration closed
  - Cannot register if team doesn't meet tournament team_size requirement
- [ ] **Manager Methods:**
  - `TournamentRegistrationManager.confirmed()`: Returns confirmed registrations
  - `TournamentRegistrationManager.checked_in()`: Returns checked-in teams
  - `TournamentRegistrationManager.for_tournament(tournament)`: Filter by tournament
- [ ] **Instance Methods:**
  - `can_check_in()`: Returns True if check-in window open and status=CONFIRMED
  - `check_in()`: Updates status to CHECKED_IN, sets checked_in_at
  - `confirm()`: Updates status to CONFIRMED, sets confirmed_at
  - `cancel()`: Updates status to CANCELLED
- [ ] **Signals:**
  - `post_save`: Send email notification to team captain on status change
  - `pre_delete`: Prevent deletion if tournament started
- [ ] Database migration created and applied
- [ ] Model registered in admin

**Dependencies:**
- BE-006 (Tournament model)
- BE-011 (Team model)

**Technical Notes:**
- Use Django signals for email notifications (decoupled from model logic)
- Payment proof uploaded by team, verified by organizer
- Seed assignment done manually by organizer or auto-assigned
- Reference: PROPOSAL_PART_3.md Section 3.5 (Registration Model)

**Files to Create/Modify:**
- `apps/tournaments/models.py` (add TournamentRegistration)
- `apps/tournaments/migrations/000X_registration.py` (auto-generated)
- `apps/tournaments/signals.py` (create registration signals)
- `apps/tournaments/admin.py` (register TournamentRegistrationAdmin)

**TournamentRegistration Model Example:**
```python
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid

class TournamentRegistrationManager(models.Manager):
    def confirmed(self):
        return self.filter(status='CONFIRMED')
    
    def checked_in(self):
        return self.filter(status='CHECKED_IN')
    
    def for_tournament(self, tournament):
        return self.filter(tournament=tournament).select_related('team')

class TournamentRegistration(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CHECKED_IN', 'Checked In'),
        ('CANCELLED', 'Cancelled'),
        ('DISQUALIFIED', 'Disqualified'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('NOT_REQUIRED', 'Not Required'),
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('REFUNDED', 'Refunded'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tournament = models.ForeignKey('tournaments.Tournament', on_delete=models.CASCADE, related_name='registrations')
    team = models.ForeignKey('teams.Team', on_delete=models.CASCADE, related_name='tournament_registrations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='NOT_REQUIRED')
    payment_proof = models.FileField(upload_to='registrations/payments/', null=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    seed = models.IntegerField(null=True, blank=True, help_text="Bracket seeding (1 = strongest)")
    notes = models.TextField(blank=True)
    
    objects = TournamentRegistrationManager()
    
    class Meta:
        unique_together = [['tournament', 'team']]
        ordering = ['registered_at']
        indexes = [
            models.Index(fields=['tournament', 'status']),
        ]
    
    def clean(self):
        # Validate tournament not full
        if self.tournament.is_full():
            raise ValidationError('Tournament is full')
        
        # Validate registration window
        if not self.tournament.can_register():
            raise ValidationError('Registration is closed')
        
        # Validate team size
        if not self.team.can_join_tournament(self.tournament):
            raise ValidationError(
                f'Team must have at least {self.tournament.team_size} members'
            )
        
        # Set payment status based on entry fee
        if self.tournament.entry_fee == 0:
            self.payment_status = 'NOT_REQUIRED'
        elif self.payment_status == 'NOT_REQUIRED' and self.tournament.entry_fee > 0:
            self.payment_status = 'PENDING'
    
    def can_check_in(self):
        now = timezone.now()
        return (self.status == 'CONFIRMED' and 
                self.tournament.check_in_start <= now <= self.tournament.check_in_end)
    
    def check_in(self):
        if not self.can_check_in():
            raise ValidationError('Cannot check in at this time')
        self.status = 'CHECKED_IN'
        self.checked_in_at = timezone.now()
        self.save()
    
    def confirm(self):
        if self.status != 'PENDING':
            raise ValidationError('Only pending registrations can be confirmed')
        self.status = 'CONFIRMED'
        self.confirmed_at = timezone.now()
        self.save()
    
    def cancel(self):
        if self.status in ['CHECKED_IN', 'DISQUALIFIED']:
            raise ValidationError('Cannot cancel checked-in or disqualified registration')
        self.status = 'CANCELLED'
        self.save()
    
    def __str__(self):
        return f"{self.team.name} - {self.tournament.title}"
```

**Signal Example (signals.py):**
```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import TournamentRegistration

@receiver(post_save, sender=TournamentRegistration)
def notify_registration_status_change(sender, instance, created, **kwargs):
    """Send email notification on registration status change"""
    if created:
        # Send registration confirmation email
        subject = f"Registration Received - {instance.tournament.title}"
        message = f"Your team {instance.team.name} has been registered. Status: {instance.status}"
        # Send email using Celery task
    elif instance.status == 'CONFIRMED':
        subject = f"Registration Confirmed - {instance.tournament.title}"
        message = f"Your team {instance.team.name} has been confirmed!"
        # Send email
```

**Testing:**
- Create registration: Tournament + Team → verify unique constraint
- Register when full → ValidationError
- Register with insufficient team size → ValidationError
- Test `can_check_in()`: Returns True during check-in window
- Call `check_in()` → status updated to CHECKED_IN
- Test signal: Status change → email sent to captain
- Run migration: `python manage.py makemigrations tournaments && python manage.py migrate`

---

## 📋 Task Cards - Quality Track (5 points)

### **QA-005: Tournament & Team Model Tests**

**Type:** Story  
**Priority:** High (P1)  
**Story Points:** 3  
**Assignee:** QA Engineer  
**Sprint:** Sprint 3  
**Epic:** Epic 2 - Tournament Engine

**Description:**
Write comprehensive unit tests for Tournament, GameConfig, Team, and TournamentRegistration models. Test model methods, validation, constraints, manager queries, and signals.

**Acceptance Criteria:**
- [ ] **Tournament Model Tests:**
  - Test field validations (date ranges, max_teams power of 2, team_size)
  - Test `clean()` method raises ValidationError for invalid data
  - Test manager methods: `published()`, `upcoming()`, `ongoing()`
  - Test instance methods: `can_register()`, `is_full()`, `get_absolute_url()`
  - Test slug auto-generation from title
  - Test status workflow transitions
- [ ] **GameConfig Model Tests:**
  - Test slug auto-generation
  - Test `validate_team_size()` method
  - Test `get_platform_choices()` returns list
  - Test manager methods: `active()`, `by_type()`
- [ ] **Team Model Tests:**
  - Test slug generation from name + tag
  - Test unique_together constraint (name, tag)
  - Test `get_members()` returns active members only
  - Test `has_member()` checks membership
  - Test `can_join_tournament()` validates team size
  - Test TeamMember through model
- [ ] **TournamentRegistration Model Tests:**
  - Test unique_together constraint (tournament, team)
  - Test `can_check_in()` validates time window and status
  - Test `check_in()`, `confirm()`, `cancel()` methods
  - Test validation: cannot register when full/closed
  - Test signal: post_save sends email notification
- [ ] All tests use pytest fixtures and factory_boy
- [ ] Test coverage >85% for models
- [ ] Tests run in CI pipeline

**Dependencies:**
- QA-001 (pytest setup)
- BE-006, BE-007, BE-011, BE-013 (Models)

**Technical Notes:**
- Use `factory_boy` for test data generation (avoid manual object creation)
- Use `freezegun` to mock datetime for time-based tests
- Test database transactions with `pytest-django`'s `transactional_db`
- Reference: PROPOSAL_PART_5.md Section 5.1 (Backend Testing)

**Files to Create/Modify:**
- `apps/tournaments/tests/test_models.py` (new)
- `apps/game_configs/tests/test_models.py` (new)
- `apps/teams/tests/test_models.py` (new)
- `apps/tournaments/tests/factories.py` (new - factory_boy factories)
- `apps/teams/tests/factories.py` (new)

**Test Example (test_models.py):**
```python
import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from freezegun import freeze_time
from apps.tournaments.models import Tournament
from apps.tournaments.tests.factories import TournamentFactory, GameConfigFactory, UserFactory

@pytest.mark.django_db
class TestTournamentModel:
    def test_slug_auto_generation(self):
        """Test slug is auto-generated from title"""
        tournament = TournamentFactory(title="Summer Cup 2025")
        assert tournament.slug == "summer-cup-2025"
    
    def test_max_teams_power_of_2_validation(self):
        """Test max_teams must be power of 2 for elimination formats"""
        with pytest.raises(ValidationError):
            tournament = TournamentFactory.build(
                format='SINGLE_ELIMINATION',
                max_teams=15  # Not power of 2
            )
            tournament.full_clean()
    
    def test_registration_end_before_start_validation(self):
        """Test registration_end must be before tournament_start"""
        with pytest.raises(ValidationError):
            tournament = TournamentFactory.build(
                registration_end=timezone.now() + timezone.timedelta(days=10),
                tournament_start=timezone.now() + timezone.timedelta(days=5)
            )
            tournament.full_clean()
    
    def test_can_register_during_window(self):
        """Test can_register returns True during registration window"""
        now = timezone.now()
        tournament = TournamentFactory(
            status='PUBLISHED',
            registration_start=now - timezone.timedelta(days=1),
            registration_end=now + timezone.timedelta(days=7),
            max_teams=16
        )
        assert tournament.can_register() is True
    
    def test_cannot_register_when_full(self):
        """Test can_register returns False when max_teams reached"""
        tournament = TournamentFactory(
            status='PUBLISHED',
            max_teams=4
        )
        # Create 4 confirmed registrations
        for _ in range(4):
            TournamentRegistrationFactory(
                tournament=tournament,
                status='CONFIRMED'
            )
        assert tournament.is_full() is True
        assert tournament.can_register() is False
    
    def test_tournament_manager_published(self):
        """Test TournamentManager.published() returns only published tournaments"""
        TournamentFactory(status='DRAFT')
        published = TournamentFactory(status='PUBLISHED')
        TournamentFactory(status='CANCELLED')
        
        assert Tournament.objects.published().count() == 1
        assert Tournament.objects.published().first() == published
    
    @freeze_time("2025-06-01 10:00:00")
    def test_tournament_manager_upcoming(self):
        """Test TournamentManager.upcoming() returns future tournaments"""
        past = TournamentFactory(
            status='PUBLISHED',
            tournament_start=timezone.now() - timezone.timedelta(days=1)
        )
        upcoming = TournamentFactory(
            status='PUBLISHED',
            tournament_start=timezone.now() + timezone.timedelta(days=7)
        )
        
        assert Tournament.objects.upcoming().count() == 1
        assert Tournament.objects.upcoming().first() == upcoming

@pytest.mark.django_db
class TestTeamModel:
    def test_slug_generation_from_name_and_tag(self):
        """Test slug generated from name + tag"""
        team = TeamFactory(name="Team Liquid", tag="TL")
        assert team.slug == "team-liquid-tl"
    
    def test_unique_together_name_tag(self):
        """Test name + tag combination must be unique"""
        TeamFactory(name="Team Alpha", tag="TA")
        with pytest.raises(Exception):  # IntegrityError
            TeamFactory(name="Team Alpha", tag="TA")
    
    def test_has_member_returns_true_for_active_members(self):
        """Test has_member() checks active membership"""
        team = TeamFactory()
        user = UserFactory()
        TeamMemberFactory(team=team, player=user, is_active=True)
        
        assert team.has_member(user) is True
    
    def test_can_join_tournament_validates_team_size(self):
        """Test can_join_tournament() checks sufficient members"""
        team = TeamFactory()
        tournament = TournamentFactory(team_size=5)
        
        # Add 3 members (insufficient)
        for _ in range(3):
            TeamMemberFactory(team=team, is_active=True)
        assert team.can_join_tournament(tournament) is False
        
        # Add 2 more members (now sufficient)
        for _ in range(2):
            TeamMemberFactory(team=team, is_active=True)
        assert team.can_join_tournament(tournament) is True

@pytest.mark.django_db
class TestTournamentRegistrationModel:
    def test_unique_together_tournament_team(self):
        """Test tournament + team combination must be unique"""
        tournament = TournamentFactory()
        team = TeamFactory()
        TournamentRegistrationFactory(tournament=tournament, team=team)
        
        with pytest.raises(Exception):  # IntegrityError
            TournamentRegistrationFactory(tournament=tournament, team=team)
    
    def test_check_in_during_window(self):
        """Test check_in() works during check-in window"""
        now = timezone.now()
        tournament = TournamentFactory(
            check_in_start=now - timezone.timedelta(minutes=30),
            check_in_end=now + timezone.timedelta(minutes=30)
        )
        registration = TournamentRegistrationFactory(
            tournament=tournament,
            status='CONFIRMED'
        )
        
        assert registration.can_check_in() is True
        registration.check_in()
        assert registration.status == 'CHECKED_IN'
        assert registration.checked_in_at is not None
    
    def test_cannot_register_when_full(self):
        """Test validation prevents registration when tournament full"""
        tournament = TournamentFactory(max_teams=2)
        team1 = TeamFactory()
        team2 = TeamFactory()
        team3 = TeamFactory()
        
        TournamentRegistrationFactory(tournament=tournament, team=team1, status='CONFIRMED')
        TournamentRegistrationFactory(tournament=tournament, team=team2, status='CONFIRMED')
        
        with pytest.raises(ValidationError):
            registration = TournamentRegistrationFactory.build(tournament=tournament, team=team3)
            registration.full_clean()
```

**Factory Example (factories.py):**
```python
import factory
from factory.django import DjangoModelFactory
from django.utils import timezone
from apps.tournaments.models import Tournament, TournamentRegistration
from apps.accounts.models import User

class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
    
    email = factory.Sequence(lambda n: f'user{n}@example.com')
    username = factory.Sequence(lambda n: f'user{n}')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')

class GameConfigFactory(DjangoModelFactory):
    class Meta:
        model = 'game_configs.GameConfig'
    
    name = factory.Sequence(lambda n: f'Game {n}')
    slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(' ', '-'))
    game_type = 'VALORANT'
    min_team_size = 1
    max_team_size = 5

class TournamentFactory(DjangoModelFactory):
    class Meta:
        model = Tournament
    
    title = factory.Sequence(lambda n: f'Tournament {n}')
    organizer = factory.SubFactory(UserFactory)
    game = factory.SubFactory(GameConfigFactory)
    status = 'PUBLISHED'
    format = 'SINGLE_ELIMINATION'
    team_size = 5
    max_teams = 16
    prize_pool = 1000
    registration_start = factory.LazyFunction(lambda: timezone.now())
    registration_end = factory.LazyFunction(lambda: timezone.now() + timezone.timedelta(days=7))
    tournament_start = factory.LazyFunction(lambda: timezone.now() + timezone.timedelta(days=14))
    check_in_start = factory.LazyFunction(lambda: timezone.now() + timezone.timedelta(days=13, hours=22))
    check_in_end = factory.LazyFunction(lambda: timezone.now() + timezone.timedelta(days=14, hours=-1))
```

**Testing:**
- Run all model tests: `pytest apps/tournaments/tests/test_models.py -v`
- Run with coverage: `pytest apps/tournaments/tests/test_models.py --cov=apps.tournaments.models`
- Verify coverage >85%: `pytest --cov=apps.tournaments.models --cov-report=term-missing`
- Verify tests pass in CI pipeline

---

### **QA-006: Tournament & Team API Tests**

**Type:** Story  
**Priority:** High (P1)  
**Story Points:** 2  
**Assignee:** QA Engineer  
**Sprint:** Sprint 3  
**Epic:** Epic 2 - Tournament Engine

**Description:**
Write integration tests for Tournament and Team API endpoints. Test CRUD operations, filtering, search, permissions, validation, and custom actions.

**Acceptance Criteria:**
- [ ] **Tournament API Tests:**
  - Test `GET /api/tournaments/` returns list with pagination
  - Test `GET /api/tournaments/<slug>/` returns detail
  - Test `POST /api/tournaments/` creates tournament (authenticated)
  - Test `PUT /api/tournaments/<slug>/` updates tournament (organizer only)
  - Test `DELETE /api/tournaments/<slug>/` deletes tournament (organizer only)
  - Test `POST /api/tournaments/<slug>/publish/` publishes tournament
  - Test `POST /api/tournaments/<slug>/cancel/` cancels tournament
  - Test filtering: `?game=valorant`, `?status=PUBLISHED`
  - Test search: `?search=summer`
  - Test permissions: Unauthenticated cannot create/update
  - Test validation: Invalid data returns 400 Bad Request
- [ ] **Team API Tests:**
  - Test `GET /api/teams/` returns list
  - Test `GET /api/teams/<slug>/` returns detail with members
  - Test `POST /api/teams/` creates team (authenticated)
  - Test `PUT /api/teams/<slug>/` updates team (captain only)
  - Test `GET /api/teams/<slug>/members/` returns members list
  - Test `POST /api/teams/<slug>/add_member/` adds member (captain only)
  - Test `DELETE /api/teams/<slug>/members/<user_id>/` removes member
  - Test `POST /api/teams/<slug>/transfer_captain/` transfers captain
  - Test permissions: Non-captain cannot update/delete team
  - Test validation: Cannot add duplicate members
- [ ] **GameConfig API Tests:**
  - Test `GET /api/games/` returns active games
  - Test `GET /api/games/<slug>/` returns game detail
  - Test response includes `tournament_count` field
  - Test caching: Second request faster
- [ ] All tests use DRF's `APIClient` and `APITestCase`
- [ ] Test coverage >80% for API views
- [ ] Tests run in CI pipeline

**Dependencies:**
- QA-005 (Model tests and factories)
- BE-008, BE-009, BE-012 (API endpoints)

**Technical Notes:**
- Use `rest_framework.test.APIClient` for API requests
- Use `force_authenticate(user)` to simulate authenticated requests
- Test status codes: 200, 201, 400, 403, 404
- Test response JSON structure matches serializers
- Reference: PROPOSAL_PART_5.md Section 5.1 (API Testing)

**Files to Create/Modify:**
- `apps/tournaments/tests/test_api.py` (new)
- `apps/teams/tests/test_api.py` (new)
- `apps/game_configs/tests/test_api.py` (new)

**API Test Example (test_api.py):**
```python
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from apps.tournaments.models import Tournament
from apps.tournaments.tests.factories import TournamentFactory, UserFactory, GameConfigFactory

@pytest.mark.django_db
class TestTournamentAPI:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.game = GameConfigFactory()
    
    def test_list_tournaments(self):
        """Test GET /api/tournaments/ returns list"""
        TournamentFactory.create_batch(5, status='PUBLISHED')
        
        url = reverse('tournament-list')
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 5
    
    def test_retrieve_tournament(self):
        """Test GET /api/tournaments/<slug>/ returns detail"""
        tournament = TournamentFactory(title="Summer Cup")
        
        url = reverse('tournament-detail', kwargs={'slug': tournament.slug})
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == "Summer Cup"
        assert 'organizer' in response.data
        assert 'game' in response.data
    
    def test_create_tournament_authenticated(self):
        """Test POST /api/tournaments/ creates tournament"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('tournament-list')
        data = {
            'title': 'New Tournament',
            'game': self.game.slug,
            'format': 'SINGLE_ELIMINATION',
            'team_size': 5,
            'max_teams': 16,
            'prize_pool': 1000,
            'registration_start': '2025-06-01T00:00:00Z',
            'registration_end': '2025-06-15T23:59:59Z',
            'tournament_start': '2025-06-20T10:00:00Z',
            'check_in_start': '2025-06-20T08:00:00Z',
            'check_in_end': '2025-06-20T09:30:00Z',
        }
        response = self.client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'New Tournament'
        assert response.data['organizer']['id'] == str(self.user.id)
    
    def test_create_tournament_unauthenticated(self):
        """Test POST /api/tournaments/ requires authentication"""
        url = reverse('tournament-list')
        data = {'title': 'New Tournament'}
        response = self.client.post(url, data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_update_tournament_organizer_only(self):
        """Test PUT /api/tournaments/<slug>/ requires organizer"""
        tournament = TournamentFactory(organizer=self.user)
        other_user = UserFactory()
        
        url = reverse('tournament-detail', kwargs={'slug': tournament.slug})
        data = {'title': 'Updated Title'}
        
        # Organizer can update
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(url, data)
        assert response.status_code == status.HTTP_200_OK
        
        # Other user cannot update
        self.client.force_authenticate(user=other_user)
        response = self.client.patch(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_publish_tournament(self):
        """Test POST /api/tournaments/<slug>/publish/ publishes tournament"""
        tournament = TournamentFactory(organizer=self.user, status='DRAFT')
        self.client.force_authenticate(user=self.user)
        
        url = reverse('tournament-publish', kwargs={'slug': tournament.slug})
        response = self.client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        tournament.refresh_from_db()
        assert tournament.status == 'PUBLISHED'
    
    def test_filter_by_game(self):
        """Test GET /api/tournaments/?game=<slug> filters by game"""
        game1 = GameConfigFactory(slug='valorant')
        game2 = GameConfigFactory(slug='efootball')
        TournamentFactory.create_batch(3, game=game1)
        TournamentFactory.create_batch(2, game=game2)
        
        url = reverse('tournament-list')
        response = self.client.get(url, {'game': 'valorant'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 3
    
    def test_search_tournaments(self):
        """Test GET /api/tournaments/?search=<query> searches by title"""
        TournamentFactory(title="Summer Valorant Cup")
        TournamentFactory(title="Winter eFoot ball League")
        TournamentFactory(title="Summer CS:GO Open")
        
        url = reverse('tournament-list')
        response = self.client.get(url, {'search': 'summer'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2

@pytest.mark.django_db
class TestTeamAPI:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
    
    def test_create_team_sets_creator_as_captain(self):
        """Test POST /api/teams/ sets creator as captain"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('team-list')
        data = {
            'name': 'Team Alpha',
            'tag': 'TA',
            'description': 'Pro team',
        }
        response = self.client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['captain']['id'] == str(self.user.id)
    
    def test_add_member_captain_only(self):
        """Test POST /api/teams/<slug>/add_member/ requires captain"""
        team = TeamFactory(captain=self.user)
        new_member = UserFactory()
        other_user = UserFactory()
        
        url = reverse('team-add-member', kwargs={'slug': team.slug})
        data = {'user_id': str(new_member.id), 'role': 'PLAYER'}
        
        # Captain can add member
        self.client.force_authenticate(user=self.user)
        response = self.client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        
        # Non-captain cannot add member
        self.client.force_authenticate(user=other_user)
        response = self.client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_transfer_captain(self):
        """Test POST /api/teams/<slug>/transfer_captain/ changes captain"""
        team = TeamFactory(captain=self.user)
        new_captain = UserFactory()
        TeamMemberFactory(team=team, player=new_captain, role='PLAYER')
        
        self.client.force_authenticate(user=self.user)
        url = reverse('team-transfer-captain', kwargs={'slug': team.slug})
        data = {'new_captain_id': str(new_captain.id)}
        response = self.client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        team.refresh_from_db()
        assert team.captain == new_captain
```

**Testing:**
- Run all API tests: `pytest apps/tournaments/tests/test_api.py -v`
- Run with coverage: `pytest apps/tournaments/tests/test_api.py --cov=apps.tournaments.views`
- Verify all status codes correct (200, 201, 400, 403, 404)
- Verify tests pass in CI pipeline

---

## 📊 Sprint 3 Summary

**Total Story Points:** 50  
**Total Tasks:** 10  
**Completion Criteria:** All tasks pass QA, API endpoints functional, test coverage >80%

**Team Allocation:**
- Backend Dev 1: BE-006, BE-008, BE-013 (20 points)
- Backend Dev 2: BE-007, BE-009, BE-011 (16 points)
- Backend Dev 3: BE-010, BE-012 (9 points)
- QA Engineer: QA-005, QA-006 (5 points)

**Definition of Done:**
All committed stories are code-complete, reviewed, tested, and deployed on staging with no high-priority bugs.

**Integration Review:**
- **API Contract Review:** Wednesday 2 PM - Backend & Frontend leads align on tournament/team API responses
- **Demo:** Friday 3 PM - Demo tournament/team CRUD to PM & stakeholders

---

**Document Location:** `Documents/WorkList/Sprint_03_Week_03_Tasks.md`  
**Last Updated:** November 3, 2025  
**Version:** v1.0
