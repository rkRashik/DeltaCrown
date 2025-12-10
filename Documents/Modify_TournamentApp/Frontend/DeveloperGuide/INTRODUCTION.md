# DeltaCrown Frontend Developer Introduction

**Welcome to the DeltaCrown Tournament Platform Frontend**

This guide provides a comprehensive introduction to the DeltaCrown frontend architecture, explaining how it integrates with the backend services built across Phases 1-9 of the development roadmap.

---

## Table of Contents

1. [Overview](#overview)
2. [What is DeltaCrown?](#what-is-deltacrown)
3. [Frontend Architecture Principles](#frontend-architecture-principles)
4. [Backend Integration Overview](#backend-integration-overview)
   - [Phase 1: Architecture Foundations](#phase-1-architecture-foundations)
   - [Phase 2: Game Rules & Configuration](#phase-2-game-rules--configuration)
   - [Phase 3: Tournament Format Engine](#phase-3-tournament-format-engine)
   - [Phase 4: TournamentOps Core Workflows](#phase-4-tournamentops-core-workflows)
   - [Phase 5: Smart Registration System](#phase-5-smart-registration-system)
   - [Phase 6: Result Pipeline & Disputes](#phase-6-result-pipeline--disputes)
   - [Phase 7: Organizer Console](#phase-7-organizer-console)
   - [Phase 8: Event-Driven Stats & History](#phase-8-event-driven-stats--history)
   - [Phase 9: Frontend Developer Support](#phase-9-frontend-developer-support)
5. [Technology Stack](#technology-stack)
6. [Key Concepts](#key-concepts)
7. [Data Flow Architecture](#data-flow-architecture)
8. [Authentication & Authorization](#authentication--authorization)
9. [Development Workflow](#development-workflow)
10. [Next Steps](#next-steps)

---

## Overview

The DeltaCrown frontend is a **Next.js 14+ application** built with the **App Router** architecture, providing a comprehensive tournament management interface for three primary user types:

1. **Organizers** — Create and manage tournaments, configure rules, schedule matches, process results
2. **Players** — Register for tournaments, view match schedules, submit results, track stats
3. **Staff** — Assist with tournament operations, moderate disputes, manage scheduling

This frontend application is the culmination of **9 phases of backend development**, each contributing critical services and data models that the UI consumes through a type-safe TypeScript SDK.

---

## What is DeltaCrown?

**DeltaCrown** is a comprehensive esports tournament platform designed to handle:

- **Multiple Game Support** — Configure game-specific rules, player identity requirements, team compositions
- **Flexible Tournament Formats** — Single elimination, double elimination, round-robin, Swiss, group stages
- **Smart Registration** — Eligibility validation, team auto-fill, payment processing, waitlists
- **Automated Scheduling** — Intelligent match scheduling with conflict detection and venue management
- **Result Management** — Multi-stage result pipeline with validation, disputes, and approval workflows
- **Statistics & Leaderboards** — Real-time player/team stats, ELO ratings, tier systems, seasonal rankings
- **Event-Driven Architecture** — Asynchronous event processing for stats updates, notifications, analytics

The platform supports both **solo players** and **team-based** competitions, with comprehensive analytics and history tracking.

---

## Frontend Architecture Principles

The DeltaCrown frontend follows these core architectural principles:

### 1. **Type Safety First**

Every API interaction is **fully typed** using TypeScript interfaces generated from the backend OpenAPI schema. This ensures:

- Compile-time validation of API requests/responses
- IntelliSense autocomplete for all data structures
- Refactoring safety when backend schemas change
- Self-documenting code through explicit type definitions

```typescript
// Example: Type-safe tournament fetching
import { DeltaCrownClient } from '@/lib/api';

const client = new DeltaCrownClient({ baseUrl: process.env.NEXT_PUBLIC_API_URL });

// TypeScript knows the exact shape of TournamentDetail
const tournament: TournamentDetail = await client.tournaments.get(tournamentId);

// Auto-complete for all tournament properties
console.log(tournament.name, tournament.status, tournament.prize_pool);
```

### 2. **DTO-Based Communication**

The frontend **never** directly accesses backend ORM models. All data flows through **Data Transfer Objects (DTOs)**:

- Backend services expose DTOs through REST APIs
- Frontend SDK consumes DTOs as TypeScript types
- Clear contract between frontend and backend layers
- Changes to database schema don't break frontend

**Backend DTO Example** (Python):
```python
@dataclass
class TournamentDTO:
    id: int
    name: str
    game_slug: str
    format: str
    status: str
    max_participants: int
    start_date: datetime
    end_date: datetime
    prize_pool: Optional[Decimal]
```

**Frontend Type** (TypeScript):
```typescript
interface TournamentDTO {
  id: number;
  name: string;
  game_slug: string;
  format: string;
  status: string;
  max_participants: number;
  start_date: string; // ISO 8601
  end_date: string;
  prize_pool?: string; // Decimal as string
}
```

### 3. **SDK-Driven API Consumption**

All API calls go through the **DeltaCrown TypeScript SDK** (Epic 9.2), not raw `fetch()` calls:

✅ **Good** — Using SDK:
```typescript
const tournaments = await client.tournaments.list({ status: 'open', game_slug: 'valorant' });
```

❌ **Bad** — Raw fetch:
```typescript
const response = await fetch('/api/tournaments/?status=open&game_slug=valorant');
const tournaments = await response.json(); // No type safety!
```

**Benefits:**
- Centralized error handling
- Automatic auth token injection
- Request/response interceptors
- Retry logic for failed requests
- Type-safe parameters and responses

### 4. **Design Token System**

All styling uses **design tokens** from Epic 9.3, never hard-coded values:

✅ **Good** — Using design tokens:
```tsx
<div className="bg-primary-500 text-white p-4 rounded-md shadow-md">
  Tournament Card
</div>
```

❌ **Bad** — Hard-coded values:
```tsx
<div className="bg-blue-600 text-white p-4 rounded shadow">
  Tournament Card
</div>
```

Design tokens are defined in `design-tokens.json` and consumed through Tailwind CSS configuration.

### 5. **Component-Driven Architecture**

The UI is built from **reusable, composable components**:

- **Atomic Design** — Atoms (Button, Input) → Molecules (Card, Modal) → Organisms (TournamentCard, MatchList)
- **Compound Components** — Parent components with composable children (e.g., `Card.Header`, `Card.Content`, `Card.Footer`)
- **Accessibility First** — WCAG 2.1 AA compliance built into all components
- **Responsive by Default** — Mobile-first design with breakpoint utilities

### 6. **Server Components + Client Components**

Next.js App Router uses **React Server Components (RSC)** by default:

- **Server Components** — Data fetching, static rendering, SEO optimization
- **Client Components** — Interactive features, state management, event handlers

```tsx
// app/tournaments/page.tsx (Server Component - NO 'use client')
export default async function TournamentsPage() {
  const tournaments = await client.tournaments.list(); // Fetched on server
  return <TournamentGrid tournaments={tournaments} />;
}

// components/TournamentGrid.tsx (Client Component - HAS 'use client')
'use client';
export function TournamentGrid({ tournaments }: Props) {
  const [filter, setFilter] = useState('all');
  // Client-side filtering, interaction
  return <div>...</div>;
}
```

### 7. **Provider Pattern for Global State**

Global concerns (theme, auth, queries, toasts) are managed through **React Context providers**:

- `ThemeProvider` — Dark/light mode toggle
- `AuthProvider` — User authentication state
- `QueryProvider` — React Query cache configuration
- `ToastProvider` — Global notification system

All providers are wrapped in the root layout (`app/layout.tsx`).

---

## Backend Integration Overview

The DeltaCrown backend was built across **9 phases** (Weeks 1-40). Here's how each phase contributes to the frontend:

### Phase 1: Architecture Foundations

**Goal:** Establish clean service boundaries and adapter pattern

**Backend Deliverables:**
- `TournamentOpsService` — Core business logic orchestrator
- Adapter pattern — Isolates ORM access from business logic
- DTO layer — Type-safe data contracts
- Event bus — Pub/sub for cross-service communication

**Frontend Impact:**
- All API responses use DTOs (not raw Django models)
- Predictable data shapes across all endpoints
- Event-driven updates (e.g., match completion triggers stats refresh)

**Example:**
```typescript
// Frontend receives TournamentDTO from backend adapter
interface TournamentDTO {
  id: number;
  name: string;
  game_slug: string;
  format: 'single_elimination' | 'double_elimination' | 'round_robin' | 'swiss';
  status: 'draft' | 'registration_open' | 'in_progress' | 'completed' | 'cancelled';
  // ... 20+ more fields
}
```

### Phase 2: Game Rules & Configuration

**Goal:** Support multiple games with configurable rules

**Backend Deliverables:**
- `GameConfig` model — Game-specific settings (identity requirements, team size, scoring rules)
- `GameRuleSet` — Validation rules for game-specific constraints
- Player identity configs — Required fields per game (e.g., Riot ID for Valorant)

**Frontend Impact:**
- Tournament creation forms dynamically adapt to selected game
- Registration forms show game-specific identity fields
- Validation rules displayed to users before submission

**Example:**
```tsx
// Dynamic form based on game config
const gameConfig = await client.games.getConfig('valorant');

return (
  <form>
    <Input label="Tournament Name" required />
    <Select label="Game" options={games} />
    
    {gameConfig.requires_team && (
      <Input 
        label="Team Size" 
        type="number" 
        min={gameConfig.min_team_size} 
        max={gameConfig.max_team_size} 
      />
    )}
    
    {gameConfig.identity_requirements.map(field => (
      <Input key={field} label={field} required />
    ))}
  </form>
);
```

### Phase 3: Tournament Format Engine

**Goal:** Universal tournament format support (brackets, groups, Swiss)

**Backend Deliverables:**
- `BracketEngine` — Single/double elimination bracket generation
- `GroupStageEngine` — Round-robin scheduling
- `SwissEngine` — Swiss pairing algorithm
- `StageTransition` — Multi-stage tournament support (e.g., groups → knockout)

**Frontend Impact:**
- Bracket visualization components
- Stage navigation (tabs for different tournament stages)
- Match generation previews before tournament start

**Example:**
```tsx
// Display bracket structure
const bracket = await client.tournaments.getBracket(tournamentId);

return (
  <BracketVisualization 
    rounds={bracket.rounds} 
    matches={bracket.matches} 
    participants={bracket.participants} 
  />
);
```

### Phase 4: TournamentOps Core Workflows

**Goal:** Lifecycle management (create → start → complete)

**Backend Deliverables:**
- `TournamentLifecycleService` — State transitions (draft → open → started → completed)
- `MatchService` — Match creation, scheduling, result processing
- `RegistrationService` — Participant registration workflows

**Frontend Impact:**
- Tournament status badges reflect backend state
- Action buttons enabled/disabled based on lifecycle state
- Real-time status updates via polling or WebSocket

**Example:**
```tsx
// State-driven UI
<Card>
  <Card.Header>
    <Card.Title>{tournament.name}</Card.Title>
    <Badge variant={getStatusVariant(tournament.status)}>
      {tournament.status}
    </Badge>
  </Card.Header>
  
  <Card.Footer>
    {tournament.status === 'draft' && (
      <Button onClick={openRegistration}>Open Registration</Button>
    )}
    {tournament.status === 'registration_open' && (
      <Button onClick={startTournament}>Start Tournament</Button>
    )}
  </Card.Footer>
</Card>
```

### Phase 5: Smart Registration System

**Goal:** Intelligent registration with eligibility, payments, waitlists

**Backend Deliverables:**
- `EligibilityService` — Pre-registration validation (game identity, age, bans)
- `PaymentOrchestrationService` — Entry fee processing
- Team auto-fill — Automatic team creation for solo players
- Waitlist management — Overflow handling

**Frontend Impact:**
- Multi-step registration wizard
- Real-time eligibility feedback
- Payment integration (Stripe/PayPal)
- Waitlist notifications

**Example:**
```tsx
// Multi-step registration
const [step, setStep] = useState(1);

// Step 1: Check eligibility
const eligibility = await client.registrations.checkEligibility(tournamentId, userId);

if (!eligibility.is_eligible) {
  return <Alert variant="error">{eligibility.reasons.join(', ')}</Alert>;
}

// Step 2: Payment (if required)
if (tournament.entry_fee > 0) {
  return <PaymentForm amount={tournament.entry_fee} onSuccess={completeRegistration} />;
}

// Step 3: Confirmation
return <RegistrationConfirmation tournament={tournament} />;
```

### Phase 6: Result Pipeline & Disputes

**Goal:** Multi-stage result validation with dispute resolution

**Backend Deliverables:**
- `ResultSubmissionService` — Player result submission
- `ResultApprovalService` — Organizer approval workflow
- `DisputeService` — Evidence collection, voting, resolution
- Result states — Pending → Approved → Disputed → Resolved

**Frontend Impact:**
- Result submission forms for players
- Approval inbox for organizers
- Dispute resolution interface with evidence uploads
- Result history timeline

**Example:**
```tsx
// Organizer results inbox
const pendingResults = await client.results.getPending();

return (
  <div>
    <h2>Results Inbox ({pendingResults.length})</h2>
    {pendingResults.map(result => (
      <Card key={result.id}>
        <p>Match: {result.match_name}</p>
        <p>Submitted by: {result.submitted_by}</p>
        <p>Score: {result.scores.join(' - ')}</p>
        
        <Button onClick={() => approveResult(result.id)}>Approve</Button>
        <Button variant="danger" onClick={() => rejectResult(result.id)}>Reject</Button>
      </Card>
    ))}
  </div>
);
```

### Phase 7: Organizer Console

**Goal:** Comprehensive tournament management tools

**Backend Deliverables:**
- `StaffingService` — Permission management for tournament staff
- `ManualSchedulingService` — Override automatic scheduling
- `AuditLogService` — Track all organizer actions
- Help system — In-app documentation

**Frontend Impact:**
- Staff management UI (assign roles, permissions)
- Manual scheduling interface (drag-drop calendar)
- Audit log viewer with filtering
- Contextual help tooltips

**Example:**
```tsx
// Staff permission management
const staff = await client.staff.list(tournamentId);

return (
  <Table>
    <Table.Header>
      <Table.Row>
        <Table.Head>Name</Table.Head>
        <Table.Head>Role</Table.Head>
        <Table.Head>Permissions</Table.Head>
      </Table.Row>
    </Table.Header>
    <Table.Body>
      {staff.map(member => (
        <Table.Row key={member.id}>
          <Table.Cell>{member.name}</Table.Cell>
          <Table.Cell>
            <Select 
              value={member.role} 
              onChange={(role) => updateRole(member.id, role)}
              options={['admin', 'moderator', 'viewer']}
            />
          </Table.Cell>
          <Table.Cell>
            <PermissionCheckboxes 
              permissions={member.permissions} 
              onChange={(perms) => updatePermissions(member.id, perms)}
            />
          </Table.Cell>
        </Table.Row>
      ))}
    </Table.Body>
  </Table>
);
```

### Phase 8: Event-Driven Stats & History

**Goal:** Real-time statistics and historical analytics

**Backend Deliverables:**
- `UserStatsService` — Player performance tracking (W/L, KDA, streaks)
- `TeamStatsService` — Team ELO ratings, tier rankings
- `MatchHistoryService` — Historical match records
- `AnalyticsEngineService` — Leaderboards, percentile rankings, decay algorithms
- EventBus integration — Stats auto-update on match completion

**Frontend Impact:**
- Live leaderboards with real-time updates
- Player/team profile pages with stats dashboards
- Historical match records with filters
- Analytics charts (win rate trends, ELO progression)

**Example:**
```tsx
// Player stats dashboard
const userStats = await client.analytics.getUserStats(userId, { game_slug: 'valorant' });

return (
  <div>
    <StatCard 
      label="Win Rate" 
      value={`${userStats.win_rate}%`} 
      trend={{ value: 5.2, direction: 'up' }}
    />
    <StatCard 
      label="Current ELO" 
      value={userStats.elo_rating} 
      icon={getTierIcon(userStats.tier)}
    />
    <StatCard 
      label="Win Streak" 
      value={userStats.current_win_streak} 
    />
    
    <LeaderboardTable 
      entries={await client.leaderboards.get({ game: 'valorant', type: 'global' })}
    />
  </div>
);
```

### Phase 9: Frontend Developer Support

**Goal:** Empower frontend developers with comprehensive tooling

**Epic 9.1 — API Documentation Generator:**
- Swagger UI at `/api/docs/`
- ReDoc at `/api/redoc/`
- OpenAPI schema at `/api/schema/`

**Epic 9.2 — TypeScript SDK:**
- Auto-generated types from OpenAPI schema
- `DeltaCrownClient` class with 35+ methods
- Type-safe API consumption

**Epic 9.3 — UI/UX Framework:**
- Design tokens JSON (colors, typography, spacing, shadows)
- Tailwind config extending tokens
- Component library specs (35+ components)
- Accessibility guidelines (WCAG 2.1 AA)

**Epic 9.4 — Frontend Boilerplate:**
- Next.js app structure (42 files, 17 directories)
- Provider setup (Theme, Auth, Query, Toast)
- Navigation components (Header, Sidebar, UserMenu)
- 13 UI components + 4 data components
- 11 page templates with SDK integration points

**Epic 9.5 — Developer Onboarding (This Guide!):**
- Comprehensive documentation system
- Setup guides, troubleshooting, glossary
- Workflow examples, security best practices

---

## Technology Stack

### Core Framework
- **Next.js 14+** — React framework with App Router
- **React 18+** — UI library with Server Components
- **TypeScript 5+** — Type-safe JavaScript

### Styling
- **Tailwind CSS 3+** — Utility-first CSS framework
- **Design Tokens** — Centralized design system variables

### Data Fetching
- **TanStack Query (React Query)** — Server state management
- **DeltaCrown SDK** — Type-safe API client

### State Management
- **React Context** — Global state (auth, theme)
- **React Query** — Server state caching
- **useState/useReducer** — Local component state

### Forms & Validation
- **React Hook Form** — Performant form library
- **Zod** — Schema validation

### Development Tools
- **ESLint** — Code linting
- **Prettier** — Code formatting
- **TypeScript Compiler** — Type checking

---

## Key Concepts

### DTOs (Data Transfer Objects)

**Definition:** Plain data structures that define the contract between frontend and backend.

**Why DTOs?**
- Decouples frontend from backend database schema
- Explicit, versioned API contracts
- Type safety across the stack
- Easier refactoring and testing

**Example Flow:**
```
[Database] → [ORM Model] → [Adapter] → [DTO] → [API Response] → [TypeScript Type] → [React Component]
```

### Service Boundaries

The backend follows **domain-driven design** with clear service boundaries:

- `TournamentOpsService` — Tournament lifecycle, registration, match management
- `LeaderboardsService` — Stats, rankings, analytics
- `ModerationService` — Dispute resolution, user bans
- `EconomyService` — Payments, refunds, prize distribution

Frontend calls these services through **dedicated API endpoints**, never crossing boundaries directly.

### Event-Driven Updates

Many backend operations trigger **events** that update related data:

**Example:** Match completion triggers:
1. `MatchCompletedEvent` published to EventBus
2. `UserStatsService` subscribes → Updates player W/L records
3. `TeamStatsService` subscribes → Recalculates team ELO
4. `AnalyticsEngineService` subscribes → Refreshes leaderboards

**Frontend Impact:** Use polling or WebSocket subscriptions to react to these updates.

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React Components                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Dashboard │  │Tournament│  │  Match   │  │  Stats   │   │
│  │   Page   │  │   List   │  │  Detail  │  │Dashboard │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼─────────────┼─────────────┼─────────────┼──────────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │   DeltaCrown TypeScript SDK   │
        │  (Epic 9.2 - Type-safe API)  │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │      REST API Endpoints       │
        │   (Epic 9.1 - OpenAPI Docs)  │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │   TournamentOpsService Layer │
        │  (Phase 4 - Business Logic)  │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │      Adapter Layer (DTOs)     │
        │   (Phase 1 - Data Mapping)   │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │     Django ORM Models         │
        │  (Database Persistence)      │
        └──────────────────────────────┘
```

---

## Authentication & Authorization

### Authentication Flow

1. **User Login** → POST `/api/auth/login/` with credentials
2. **Backend** → Validates credentials, returns JWT access + refresh tokens
3. **Frontend** → Stores tokens in `httpOnly` cookies (secure) or `localStorage` (less secure)
4. **Subsequent Requests** → SDK automatically includes `Authorization: Bearer <token>` header
5. **Token Expiry** → SDK detects 401 response, uses refresh token to get new access token

### Authorization Roles

- **Player** — Can register for tournaments, submit results, view own stats
- **Organizer** — Can create tournaments, manage staff, approve results
- **Staff** — Can moderate disputes, view audit logs (permissions vary)
- **Admin** — Full platform access

### Role-Based UI

```tsx
import { useAuth } from '@/providers/AuthProvider';

export function TournamentActions({ tournament }: Props) {
  const { user } = useAuth();
  
  // Only show organizer actions if user is organizer
  if (user.role !== 'organizer') {
    return null;
  }
  
  return (
    <div>
      <Button onClick={startTournament}>Start Tournament</Button>
      <Button onClick={cancelTournament}>Cancel</Button>
    </div>
  );
}
```

---

## Development Workflow

### 1. Component Development

```bash
# Create a new component
touch components/MyComponent.tsx

# Use design tokens
className="bg-primary-500 text-white p-4 rounded-md"

# Add TypeScript types
interface MyComponentProps {
  title: string;
  onAction: () => void;
}
```

### 2. API Integration

```typescript
// Use the SDK, not raw fetch
import { DeltaCrownClient } from '@/lib/api';

const client = new DeltaCrownClient({ baseUrl: process.env.NEXT_PUBLIC_API_URL });

// Fetch data with type safety
const tournaments = await client.tournaments.list({ status: 'open' });
```

### 3. State Management

```tsx
// Server state (API data) → Use React Query
import { useQuery } from '@tanstack/react-query';

const { data: tournaments, isLoading, error } = useQuery({
  queryKey: ['tournaments', { status: 'open' }],
  queryFn: () => client.tournaments.list({ status: 'open' }),
});

// Local state (UI interactions) → Use useState
const [isModalOpen, setIsModalOpen] = useState(false);
```

### 4. Styling

```tsx
// Use Tailwind utilities with design tokens
<Card className="bg-surface-light dark:bg-surface-dark p-6 rounded-lg shadow-md">
  <Card.Title className="text-heading-lg font-semibold text-text-primary">
    Tournament Name
  </Card.Title>
</Card>
```

---

## Next Steps

Now that you understand the architecture, explore these guides:

1. **[PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)** — Detailed folder structure and conventions
2. **[SDK_USAGE_GUIDE.md](./SDK_USAGE_GUIDE.md)** — TypeScript SDK examples and patterns
3. **[COMPONENTS_GUIDE.md](./COMPONENTS_GUIDE.md)** — UI component library reference
4. **[WORKFLOW_GUIDE.md](./WORKFLOW_GUIDE.md)** — Common tournament workflows
5. **[LOCAL_SETUP.md](./LOCAL_SETUP.md)** — Development environment setup

---

**Happy coding! 🚀**
