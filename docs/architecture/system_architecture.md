# DeltaCrown System Architecture

## Overview

DeltaCrown is a Django-based tournament management platform with real-time features, supporting multiple esports games with team/solo tournaments, leaderboards, and an integrated economy system.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend Layer                        │
│                    (React/Next.js - Future)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST API + WebSocket
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                     Django Backend (Backend V1)              │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   REST API  │  │  WebSockets  │  │  Admin Panel │      │
│  │    (DRF)    │  │  (Channels)  │  │   (Django)   │      │
│  └─────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Business Logic Layer                    │   │
│  │  • Tournament Services  • Team Services             │   │
│  │  • Leaderboard Engine   • Economy Services          │   │
│  │  • Bracket Generator    • Notification System       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   Data Layer                         │   │
│  │  • Django ORM       • Transactions                   │   │
│  │  • Models           • Query Optimization             │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ↓              ↓               ↓
   ┌─────────┐   ┌─────────┐    ┌──────────┐
   │PostgreSQL│   │  Redis  │    │  Celery  │
   │ Database │   │  Cache  │    │  Workers │
   └─────────┘   └─────────┘    └──────────┘
```

---

## Component Architecture

### 1. REST API Layer (Django REST Framework)

**Purpose**: HTTP-based CRUD operations and tournament management

**Components**:
- `apps/tournaments/api/` - Tournament CRUD, registration, check-in
- `apps/teams/api/` - Team management, invitations
- `apps/economy/api/` - Wallet operations, transactions
- `apps/leaderboards/api/` - Global and tournament rankings

**Key Features**:
- JWT authentication
- Custom exception handling (Module 9.5)
- Request logging with correlation IDs
- Prometheus metrics
- Pagination & filtering

**Technology Stack**:
- Django REST Framework 3.15.2
- Simple JWT for authentication
- Custom middleware for logging/metrics

---

### 2. WebSocket Layer (Django Channels)

**Purpose**: Real-time updates for tournaments, matches, and brackets

**Components**:
- `apps/tournaments/realtime/consumers.py` - WebSocket consumers
- `apps/tournaments/realtime/error_events.py` - Error handling (Module 9.5)
- `apps/tournaments/events/` - Event broadcasting

**Message Types**:
- Tournament status updates (DRAFT → PUBLISHED → LIVE → COMPLETED)
- Match score updates (live scoring)
- Bracket generation events
- Registration updates

**Technology Stack**:
- Django Channels 4.1.0
- Redis as channel layer
- JWT authentication for WebSocket connections

---

### 3. Business Logic Layer

#### Tournament Services
**Location**: `apps/tournaments/services/`

**Key Services**:
- `tournament_service.py` - Tournament lifecycle management
- `registration_service.py` - Registration flow & validation
- `bracket_service.py` - Bracket generation algorithms
- `match_service.py` - Match scheduling & scoring
- `dashboard_service.py` - Organizer dashboard data

**Responsibilities**:
- Business rule enforcement
- State machine transitions
- Transaction management
- Event publishing

#### Leaderboard Engine
**Location**: `apps/leaderboards/`

**Components**:
- `engine.py` - Core ranking calculations
- `services.py` - Game-specific leaderboard logic (Valorant, eFootball)
- `tasks.py` - Background leaderboard updates (Celery)

**Features**:
- Multi-game support (Valorant, eFootball, FIFA, CS:GO)
- Configurable scoring formulas
- Incremental updates
- Historical tracking

#### Economy System
**Location**: `apps/economy/`

**Components**:
- `services.py` - Wallet operations, transfers
- `models.py` - DeltaCoin, transactions, wallet

**Features**:
- Atomic transactions
- Double-entry bookkeeping
- Entry fee collection
- Prize distribution
- Transfer validation

---

### 4. Data Layer

#### Django ORM Models

**Tournament System** (`apps/tournaments/models/`):
```
Tournament
├── fields: name, game, status, format, dates, prize_pool
├── relations: organizer (User), game (Game)
└── methods: can_register(), start_tournament(), complete()

Registration
├── fields: tournament, user, team, status, payment
├── relations: tournament (Tournament), user (User), team (Team)
└── methods: confirm(), check_in(), cancel()

Match
├── fields: tournament, round, state, score, scheduled_at
├── relations: tournament, participants, winner, teams
└── methods: start(), report_score(), complete()

Bracket
├── fields: tournament, bracket_data, current_round
├── relations: tournament (Tournament)
└── methods: generate(), advance_winners()
```

**Team System** (`apps/teams/models.py`):
```
Team
├── fields: name, tag, game, captain
├── relations: captain (User), members (TeamMember)
└── methods: add_member(), remove_member(), can_register()

TeamMember
├── fields: team, user, role, status
├── relations: team (Team), user (User)
└── methods: accept_invitation(), leave()
```

**Economy System** (`apps/economy/models.py`):
```
DeltaCoin
├── fields: user, balance, locked_balance
├── relations: user (User), transactions
└── methods: credit(), debit(), lock(), unlock()

Transaction
├── fields: user, type, amount, balance_after, metadata
├── relations: user (User), related_object (GenericFK)
└── methods: create_transfer(), validate()
```

**Leaderboard System** (`apps/leaderboards/models.py`):
```
LeaderboardEntry
├── fields: user/team, game, rating, wins, losses, rank
├── relations: user (User), team (Team), tournament
└── methods: update_rating(), recalculate_rank()
```

---

## Data Flow Diagrams

### Tournament Registration Flow

```
User Request
    ↓
[POST /api/tournaments/{id}/register/]
    ↓
JWT Authentication Middleware
    ↓
RegistrationViewSet.create()
    ↓
RegistrationService.register()
    ↓
┌───────────────────────────────────┐
│ Business Logic Validation:        │
│ 1. Tournament status check        │
│ 2. Registration window check      │
│ 3. Duplicate check                │
│ 4. Team validation (if team mode) │
│ 5. Capacity check                 │
└───────────────────────────────────┘
    ↓
Create Registration (PENDING_PAYMENT)
    ↓
EconomyService.lock_entry_fee()
    ↓
Publish Event: "registration.created"
    ↓
WebSocket Broadcast → Connected clients
    ↓
Return Response (201 Created)
```

### Match Scoring Flow

```
Organizer Request
    ↓
[POST /api/matches/{id}/report-score/]
    ↓
JWT + Permission Check (organizer only)
    ↓
MatchService.report_score()
    ↓
┌──────────────────────────────────┐
│ Business Logic:                   │
│ 1. Match state validation        │
│ 2. Score format validation       │
│ 3. Winner determination          │
└──────────────────────────────────┘
    ↓
Update Match (state=COMPLETED)
    ↓
┌──────────────────────────────────┐
│ Side Effects:                     │
│ 1. Update bracket (advance winner)│
│ 2. Update leaderboard stats      │
│ 3. Distribute prizes (if final)  │
└──────────────────────────────────┘
    ↓
Publish Event: "match.completed"
    ↓
WebSocket Broadcast → Spectators
    ↓
Celery Task: Update leaderboards
    ↓
Return Response (200 OK)
```

### Leaderboard Update Flow

```
Match Completion Event
    ↓
Celery Task: update_leaderboard(tournament_id)
    ↓
LeaderboardEngine.calculate()
    ↓
┌──────────────────────────────────┐
│ Aggregation:                      │
│ 1. Fetch all match results       │
│ 2. Calculate wins/losses          │
│ 3. Calculate rating (ELO/points) │
│ 4. Sort by rating                 │
│ 5. Assign ranks                   │
└──────────────────────────────────┘
    ↓
Bulk Update LeaderboardEntry
    ↓
Publish Event: "leaderboard.updated"
    ↓
WebSocket Broadcast → Viewers
    ↓
Cache Updated Rankings (Redis)
```

---

## State Machines

### Tournament State Machine

```
         ┌──────┐
    ┌───►│DRAFT │
    │    └───┬──┘
    │        │ publish()
    │        ↓
    │   ┌────────────┐
    │   │ PUBLISHED  │
    │   └─────┬──────┘
    │         │ start() [registration closed]
    │         ↓
    │    ┌────────┐
    │    │  LIVE  │
    │    └────┬───┘
    │         │ complete() [all matches done]
    │         ↓
    │   ┌───────────┐
    │   │ COMPLETED │
    │   └───────────┘
    │
    └──cancel() [from any state]──┐
                                   ↓
                             ┌──────────┐
                             │CANCELLED │
                             └──────────┘
```

**Transitions**:
- `DRAFT → PUBLISHED`: Tournament published (organizer action)
- `PUBLISHED → LIVE`: Tournament started (auto or manual)
- `LIVE → COMPLETED`: All matches completed (auto)
- `* → CANCELLED`: Organizer cancellation

### Match State Machine

```
    ┌─────────┐
    │ PENDING │
    └────┬────┘
         │ start()
         ↓
    ┌────────────┐
    │IN_PROGRESS │
    └─────┬──────┘
          │ report_score()
          ↓
    ┌───────────┐
    │ COMPLETED │
    └───────────┘
```

### Registration State Machine

```
    ┌─────────────────┐
    │PENDING_PAYMENT  │
    └────────┬────────┘
             │ confirm_payment()
             ↓
        ┌──────────┐
        │CONFIRMED │
        └─────┬────┘
              │ check_in()
              ↓
        ┌────────────┐
        │ CHECKED_IN │
        └────────────┘
```

---

## Database Schema (Simplified)

```sql
-- Core Tables
users
  ├── id (PK)
  ├── username
  ├── email
  └── created_at

games
  ├── id (PK)
  ├── name (valorant, efootball, etc.)
  └── config (JSON)

tournaments
  ├── id (PK)
  ├── name
  ├── game_id (FK → games)
  ├── organizer_id (FK → users)
  ├── status (enum)
  ├── format (enum)
  ├── participation_type (enum)
  ├── tournament_start (timestamp)
  ├── registration_end (timestamp)
  ├── max_participants
  └── prize_pool

registrations
  ├── id (PK)
  ├── tournament_id (FK → tournaments)
  ├── user_id (FK → users)
  ├── team_id (FK → teams, nullable)
  ├── status (enum)
  └── created_at

teams
  ├── id (PK)
  ├── name
  ├── tag
  ├── game_id (FK → games)
  ├── captain_id (FK → users)
  └── created_at

team_members
  ├── id (PK)
  ├── team_id (FK → teams)
  ├── user_id (FK → users)
  ├── role (enum)
  └── status (enum)

matches
  ├── id (PK)
  ├── tournament_id (FK → tournaments)
  ├── round
  ├── match_number
  ├── state (enum)
  ├── participant1_id (FK → registrations)
  ├── participant2_id (FK → registrations)
  ├── winner_id (FK → registrations, nullable)
  ├── score (JSON)
  └── scheduled_at

brackets
  ├── id (PK)
  ├── tournament_id (FK → tournaments, unique)
  ├── bracket_data (JSON)
  └── current_round

leaderboard_entries
  ├── id (PK)
  ├── tournament_id (FK → tournaments)
  ├── participant_id (FK → registrations)
  ├── rank
  ├── rating
  ├── wins
  ├── losses
  └── updated_at

deltacoins
  ├── id (PK)
  ├── user_id (FK → users, unique)
  ├── balance (decimal)
  └── locked_balance (decimal)

transactions
  ├── id (PK)
  ├── user_id (FK → users)
  ├── type (enum)
  ├── amount (decimal)
  ├── balance_after (decimal)
  ├── metadata (JSON)
  └── created_at
```

**Indexes** (Module 9.1 Performance Optimization):
- `idx_tournament_game_status` on `(game_id, status, is_deleted)`
- `idx_registration_tournament_user` on `(tournament_id, user_id)`
- `idx_match_tournament_state` on `(tournament_id, state)`
- `idx_payment_registration_status` on `(registration_id, status)`

---

## Technology Stack

### Backend
- **Framework**: Django 5.2.8
- **API**: Django REST Framework 3.15.2
- **WebSocket**: Django Channels 4.1.0
- **Authentication**: Simple JWT
- **Task Queue**: Celery 5.4.0
- **Database**: PostgreSQL 14+
- **Cache**: Redis 6+

### Infrastructure
- **Monitoring**: Prometheus + Grafana
- **Logging**: Structured JSON logs
- **Health Checks**: /healthz, /readyz (K8s-compatible)
- **Metrics**: django-prometheus

### Testing
- **Framework**: pytest-django 4.11.1
- **Coverage**: pytest-cov
- **Mocking**: unittest.mock
- **Fixtures**: Factory pattern

---

## Security Architecture

### Authentication Flow
```
1. User submits credentials
2. POST /api/token/ → JWT access + refresh tokens
3. Client stores tokens (secure storage)
4. Requests include: Authorization: Bearer {access_token}
5. Middleware validates JWT signature
6. Request processed with authenticated user
7. Token refresh before expiry (POST /api/token/refresh/)
```

### Authorization
- **Permission Classes**: IsAuthenticated, IsOrganizer, IsTeamCaptain
- **Row-level**: Custom permission checks in views/services
- **WebSocket**: JWT in query params or headers

### Security Features (Module 2.4)
- CSRF protection (Django middleware)
- SQL injection protection (Django ORM)
- XSS protection (Django templates, DRF escaping)
- Rate limiting (DRF throttling)
- CORS configuration (django-cors-headers)
- Password hashing (Django PBKDF2)

---

## Performance Optimizations

### Database (Module 9.1)
- **Query optimization**: select_related(), prefetch_related()
- **Composite indexes**: 4 strategic indexes on hot paths
- **Query reduction**: 90-95% reduction (20-60 → 2-5 queries per request)
- **Transaction management**: Atomic operations for consistency

### Caching
- **Redis**: Session cache, Celery results, channel layer
- **Query cache**: Leaderboard rankings cached
- **Pattern**: Cache-aside strategy

### Async Processing
- **Celery tasks**: Leaderboard updates, email notifications, cleanup
- **Background jobs**: Non-blocking for user requests
- **Retry logic**: Exponential backoff

---

## Monitoring & Observability

### Metrics (Module 9.5)
- **HTTP**: Request count, latency, error rates
- **WebSocket**: Connection count, message rate, close reasons
- **Business**: Registrations, matches, transactions

### Logging (Module 9.5)
- **Structured**: JSON format with correlation IDs
- **Levels**: DEBUG, INFO, WARNING, ERROR
- **Tracing**: X-Correlation-ID header for request tracking

### Health Checks (Module 9.5)
- `/healthz`: Liveness (always 200 if running)
- `/readyz`: Readiness (checks DB, cache)

---

## Deployment Architecture

```
┌──────────────────────────────────────────────────┐
│              Load Balancer (nginx)                │
│           SSL Termination + Static Files          │
└────────────────┬─────────────────────────────────┘
                 │
        ┌────────┼────────┐
        ↓        ↓        ↓
    ┌──────┐ ┌──────┐ ┌──────┐
    │Django│ │Django│ │Django│  ← Gunicorn workers
    │ App  │ │ App  │ │ App  │
    └───┬──┘ └───┬──┘ └───┬──┘
        └────────┼────────┘
                 ↓
        ┌────────────────┐
        │   PostgreSQL   │  ← Primary database
        │   (Primary)    │
        └────────────────┘
                 ↓
        ┌────────────────┐
        │     Redis      │  ← Cache + Channel Layer
        └────────────────┘
                 ↓
        ┌────────────────┐
        │  Celery Workers│  ← Background tasks
        │   + Celery Beat│
        └────────────────┘
```

---

## API Design Principles

### RESTful Conventions
- **Resources**: Nouns (tournaments, teams, matches)
- **Actions**: HTTP verbs (GET, POST, PUT, DELETE)
- **Status codes**: Semantic (200, 201, 400, 401, 404, 500)
- **Pagination**: Cursor-based
- **Filtering**: Query parameters

### IDs-Only Responses
```json
// ✅ Correct
{
  "id": 123,
  "tournament_id": 456,
  "team_id": 789
}

// ❌ Incorrect (nested objects)
{
  "id": 123,
  "tournament": {...},
  "team": {...}
}
```

### Error Handling
- Consistent format (Module 9.5)
- Error codes for client mapping
- No sensitive data in errors

---

## Future Enhancements

- **Microservices**: Split into tournament, leaderboard, economy services
- **Event Sourcing**: Audit trail for all state changes
- **GraphQL**: Alternative API layer
- **ML Predictions**: Match outcome predictions
- **Advanced Analytics**: Player performance insights

---

## References

- **API Docs**: `docs/api/endpoint_catalog.md`
- **Setup Guide**: `docs/development/setup_guide.md`
- **Module Status**: `Documents/ExecutionPlan/Core/MAP.md`
- **Planning Docs**: `Documents/Planning/`

---

**Last Updated**: Module 9.6 (Backend V1 Finalization)
