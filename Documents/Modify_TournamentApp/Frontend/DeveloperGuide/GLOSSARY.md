# Glossary

## Table of Contents

1. [Introduction](#introduction)
2. [Tournament Operations](#tournament-operations)
3. [Backend Architecture](#backend-architecture)
4. [Frontend Development](#frontend-development)
5. [Analytics & Statistics](#analytics--statistics)
6. [Developer Workflow](#developer-workflow)

---

## Introduction

This glossary defines **key terminology** used throughout the DeltaCrown Organizer Console codebase, documentation, and team communication. Terms are organized by category for easy reference.

**Who should use this:**

- New developers onboarding to the project
- Team members clarifying domain-specific concepts
- Anyone reviewing architectural documentation

**How to use:**

- Use **Ctrl+F** (or **Cmd+F**) to search for specific terms
- Each entry includes: definition, usage context, and optional code examples
- Cross-references link to other glossary terms (marked with →)

---

## Tournament Operations

### Bracket

A tournament structure that determines how participants advance through rounds. Common types include **single elimination**, **double elimination**, and **round robin**.

**Used in:** Tournament creation, match generation

**Example:**
```typescript
const tournament = await client.tournaments.create({
  bracket_type: 'single_elimination',
  max_participants: 32,
});
```

---

### Bracket Type

The format of tournament progression. Options:

- **Single Elimination**: Lose once, you're out
- **Double Elimination**: Two losses required for elimination (winners + losers bracket)
- **Round Robin**: Every participant plays every other participant
- **Swiss**: Participants paired based on similar records

**Used in:** Tournament configuration

---

### Bye

A free advancement to the next round when there's an odd number of participants. The participant with a bye does not play a match.

**Used in:** Match generation, bracket seeding

**Example:**
```typescript
// A match with null participant_2 indicates a bye
{
  participant_1: userId,
  participant_2: null, // ← Bye
  winner: userId, // Automatically set
}
```

---

### Dispute

A formal challenge to a match result, filed by a participant who believes the outcome is incorrect. Includes evidence (screenshots, videos) and reason.

**Used in:** Results management, match history

**Example:**
```typescript
await client.disputes.create({
  match_id: matchId,
  reason: 'Opponent used banned character',
  evidence_urls: ['https://example.com/proof.mp4'],
});
```

---

### Eligibility

Criteria determining whether a user can register for a tournament. Checks include:

- **Tier** (user's skill tier matches tournament requirements)
- **Rank** (minimum rank threshold)
- **Team requirements** (solo vs team tournament)
- **Blacklist status** (banned users excluded)

**Used in:** Smart Registration (Epic 8.2)

**Example:**
```typescript
const { is_eligible, reasons } = await client.registration.checkEligibility({
  tournament_id: tournamentId,
});
// reasons: ['User tier (Bronze) below minimum (Silver)']
```

---

### Entry Fee

The cost required to register for a tournament. Can be `0.00` (free) or any positive amount.

**Used in:** Tournament configuration, payment processing

**Example:**
```typescript
const tournament = await client.tournaments.create({
  entry_fee: '25.00', // $25 entry fee
});
```

---

### Match

A single game or contest between two participants (users or teams). Tracked with:

- **Participants** (2 for most formats)
- **Score** (e.g., 3-1, 16-14)
- **Status** (scheduled, in_progress, completed, cancelled)
- **Winner** (determined by score or manual entry)

**Used in:** Scheduling, results management

**Example:**
```typescript
const match = await client.matches.get(matchId);
console.log(`${match.participant_1_name} vs ${match.participant_2_name}`);
console.log(`Score: ${match.participant_1_score} - ${match.participant_2_score}`);
```

---

### Match Lifecycle

The sequence of states a match goes through:

1. **Created** (generated but not scheduled)
2. **Scheduled** (date/time/venue assigned)
3. **In Progress** (currently being played)
4. **Completed** (result submitted and approved)
5. **Cancelled** (match voided)

**Used in:** Match management, status tracking

---

### Organizer

A user role with permissions to create and manage tournaments. Organizers can:

- Create tournaments
- Manage staff
- Schedule matches
- Approve results
- Resolve disputes

**Used in:** RBAC (→ Role-Based Access Control), authentication

**Example:**
```typescript
const { user } = useAuth();
if (user.roles.includes('organizer')) {
  // Show organizer dashboard
}
```

---

### Participant

A user or team registered for a tournament. Competes in matches and advances through the bracket.

**Used in:** Match generation, leaderboard, registration

---

### Payout

Prize distribution after tournament completion. Calculated based on:

- **Prize pool** (total available)
- **Placement** (1st, 2nd, 3rd, etc.)
- **Payout structure** (percentage per placement)

**Used in:** Prize management (Phase 7), tournament finalization

**Example:**
```typescript
// 1st place: 50%, 2nd: 30%, 3rd: 20%
const payouts = [
  { placement: 1, amount: '500.00' },
  { placement: 2, amount: '300.00' },
  { placement: 3, amount: '200.00' },
];
```

---

### Prize Pool

The total amount of money or prizes awarded in a tournament. Can be:

- Fixed (organizer-funded)
- Crowdfunded (entry fees × participants)
- Hybrid

**Used in:** Tournament configuration, payout calculation

**Example:**
```typescript
const tournament = await client.tournaments.create({
  prize_pool: '1000.00',
  prize_structure: 'percentage', // or 'fixed'
});
```

---

### Referee

A staff role with permission to manage match operations (scheduling, score updates, dispute resolution) but cannot modify tournament configuration.

**Used in:** RBAC, staff management

---

### Registration

The process of enrolling in a tournament. Steps:

1. **Eligibility check** (→ Eligibility)
2. **Payment** (if entry fee > 0)
3. **Confirmation** (registration record created)

**Used in:** Smart Registration (Epic 8.2)

**Example:**
```typescript
const registration = await client.registration.create({
  tournament_id: tournamentId,
  game_identity: 'PlayerTag#1234',
});
```

---

### Registration Window

The time period during which users can register for a tournament. Defined by:

- **Registration Start**: Opens enrollment
- **Registration End**: Closes enrollment (deadline)

**Used in:** Tournament configuration, registration validation

**Example:**
```typescript
const tournament = await client.tournaments.create({
  registration_start: '2025-06-01T00:00:00Z',
  registration_end: '2025-06-15T23:59:59Z',
});
```

---

### Result

The outcome of a match, including:

- **Score** (each participant's score)
- **Winner** (participant who won)
- **Status** (pending, approved, rejected)

**Used in:** Results management, dispute tracking

**Example:**
```typescript
await client.results.approve(resultId);
```

---

### Round

A stage in a bracket where multiple matches occur simultaneously. Examples:

- **Round of 32** (32 participants remaining)
- **Quarterfinals** (8 participants)
- **Semifinals** (4 participants)
- **Finals** (2 participants)

**Used in:** Bracket generation, match scheduling

---

### Seeding

The process of ranking participants before tournament start to ensure balanced matchups. Higher seeds face lower seeds in early rounds.

**Used in:** Bracket generation

**Example:**
```typescript
// Seed 1 vs Seed 16, Seed 2 vs Seed 15, etc.
const seeds = [
  { participant_id: user1Id, seed: 1 },
  { participant_id: user2Id, seed: 2 },
  // ...
];
```

---

### Staff

Users with tournament management permissions. Includes:

- **Organizers** (full control)
- **Referees** (match operations only)
- **Moderators** (content moderation)

**Used in:** RBAC, staff management (Epic 6.1)

---

### Stage

A phase of a tournament. Multi-stage tournaments may have:

- **Group Stage** (round robin within groups)
- **Playoffs** (single/double elimination bracket)

**Used in:** Tournament configuration, match generation

---

### Tournament Status

The lifecycle state of a tournament:

- **Draft**: Created but not published
- **Registration Open**: Accepting registrations
- **Registration Closed**: No new registrations, awaiting start
- **In Progress**: Matches being played
- **Completed**: All matches finished, winners determined
- **Cancelled**: Tournament voided

**Used in:** Tournament management, UI filtering

**Example:**
```typescript
const tournaments = await client.tournaments.list({
  status: 'in_progress',
});
```

---

### Venue

The location or platform where a match is played. Can be:

- Physical location (e.g., "Arena 1")
- Online platform (e.g., "Discord Room 3")
- Game server (e.g., "NA Server #5")

**Used in:** Match scheduling

**Example:**
```typescript
await client.scheduling.scheduleMatch({
  match_id: matchId,
  venue: 'Arena 1',
  scheduled_time: '2025-06-21T14:00:00Z',
});
```

---

## Backend Architecture

### Adapter

A design pattern that translates data between external systems and DeltaCrown's internal domain models. Used to integrate third-party APIs (payment processors, game APIs).

**Used in:** Phase 2 (Game Integration), payment processing

**Example:**
```python
# Backend code (Python)
class RiotAPIAdapter:
    def fetch_player_stats(self, summoner_name):
        # Fetch from Riot API
        # Transform to DeltaCrown PlayerStats model
        return PlayerStats(...)
```

---

### Celery

An asynchronous task queue used for background processing. Tasks include:

- ELO recalculation
- Email notifications
- Report generation

**Used in:** Phase 3 (Advanced Stats), Phase 7 (Payments)

---

### Domain Model

The core business logic representation of entities (Tournament, Match, User, etc.) independent of database schema or API contracts.

**Used in:** Backend architecture, DTOs (→ Data Transfer Object)

---

### DTO (Data Transfer Object)

A plain object that carries data between backend and frontend. DTOs:

- Are **read-only** (no methods)
- Match API response shapes exactly
- Are **strictly typed** in TypeScript SDK

**Used in:** SDK (Epic 9.2), API responses

**Example:**
```typescript
// TypeScript DTO
interface TournamentDTO {
  id: number;
  name: string;
  status: 'draft' | 'registration_open' | 'in_progress' | 'completed';
  prize_pool?: string;
  max_participants: number;
}
```

---

### Event Bus

A pub/sub system for decoupled event handling. Examples:

- `TournamentCreated` → Trigger welcome email
- `MatchCompleted` → Update leaderboard
- `DisputeResolved` → Notify participants

**Used in:** Backend event-driven architecture

---

### Façade

A design pattern providing a simplified interface to complex subsystems. DeltaCrown uses façades to expose clean API endpoints that orchestrate multiple domain services.

**Used in:** Backend API layer

**Example:**
```python
# Backend code
class TournamentFacade:
    def create_tournament(self, organizer, data):
        # Orchestrates multiple services
        tournament = TournamentService.create(data)
        PermissionService.grant(organizer, tournament)
        EventBus.publish('TournamentCreated', tournament)
        return tournament
```

---

### Schema Validation

The process of validating API request/response data against OpenAPI schemas. Ensures type safety and correct data shapes.

**Used in:** API layer, OpenAPI documentation

**Example:**
```python
# Backend code
from pydantic import BaseModel

class CreateTournamentRequest(BaseModel):
    name: str
    game: int
    bracket_type: str
    max_participants: int
```

---

### Service Layer

Backend architectural layer containing business logic. Services orchestrate domain models, repositories, and external adapters.

**Used in:** Backend architecture (all phases)

**Example:**
```python
# Backend code
class MatchService:
    def schedule_match(self, match_id, scheduled_time, venue):
        match = MatchRepository.get(match_id)
        match.schedule(scheduled_time, venue)
        MatchRepository.save(match)
        EventBus.publish('MatchScheduled', match)
```

---

## Frontend Development

### Accessibility (a11y)

Designing UIs usable by people with disabilities. DeltaCrown targets **WCAG 2.1 AA** compliance.

**Used in:** Component design (Epic 9.4), UI/UX guidelines

**Key practices:**

- Keyboard navigation (Tab, Enter, Escape, Arrows)
- ARIA attributes (`aria-label`, `aria-describedby`, `role`)
- Color contrast (4.5:1 for normal text, 3:1 for large)
- Touch targets (44×44px minimum)

**Example:**
```tsx
<button
  onClick={handleClick}
  aria-label="Delete tournament"
  className="p-2 focus:ring-2"
>
  <TrashIcon />
</button>
```

---

### Client Component

A React component that runs in the browser (client-side). Required for:

- Interactive state (hooks like `useState`, `useEffect`)
- Browser APIs (`window`, `localStorage`)
- Event handlers

**Used in:** Next.js App Router architecture

**Example:**
```tsx
'use client'; // ← Marks as Client Component

export default function Counter() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(count + 1)}>{count}</button>;
}
```

---

### Design Tokens

Centralized design values (colors, spacing, typography) defined in `design-tokens.json` and consumed by Tailwind CSS.

**Used in:** Epic 9.3 (UI/UX Framework), component styling

**Example:**
```json
// design-tokens.json
{
  "colors": {
    "brand": {
      "primary": "#3B82F6"
    }
  }
}
```

```tsx
// Usage
<div className="text-brand-primary">Hello</div>
```

---

### Hydration

The process where React attaches event listeners and state to server-rendered HTML. If server and client render differently, you get **hydration errors**.

**Used in:** Next.js SSR/CSR, troubleshooting

**Example:**
```
Warning: Text content did not match. Server: "Loading..." Client: "Data loaded"
```

**Fix:** Ensure consistent rendering or use `suppressHydrationWarning`.

---

### Responsive Breakpoints

Screen width thresholds where layout changes. DeltaCrown uses:

- **sm**: 640px (tablets)
- **md**: 768px (small desktops)
- **lg**: 1024px (large desktops)
- **xl**: 1280px (extra large screens)

**Used in:** Tailwind CSS, responsive design

**Example:**
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
  {/* 1 col on mobile, 2 on tablet, 3 on desktop */}
</div>
```

---

### Server Component

A React component that runs on the server and renders to HTML. Benefits:

- **Performance**: Zero JavaScript sent to browser
- **Direct data fetching**: Can use `async/await` for API calls
- **SEO**: Fully rendered HTML for crawlers

**Used in:** Next.js App Router, dashboard pages

**Example:**
```tsx
// app/tournaments/page.tsx (Server Component by default)
export default async function TournamentsPage() {
  const tournaments = await client.tournaments.list();
  return <div>{tournaments.map(t => <TournamentCard key={t.id} {...t} />)}</div>;
}
```

---

### SSR (Server-Side Rendering)

Rendering React components on the server to send fully-formed HTML to the browser. Improves initial load time and SEO.

**Used in:** Next.js, performance optimization

**Contrast with:**

- **CSR (Client-Side Rendering)**: JavaScript renders on browser
- **SSG (Static Site Generation)**: Pre-rendered at build time

---

### Type Safety

Ensuring variables, functions, and data structures have explicit types checked by TypeScript. Prevents runtime errors.

**Used in:** All frontend code, SDK (Epic 9.2)

**Example:**
```typescript
// ❌ Unsafe
function getTournament(id) {
  return fetch(`/api/tournaments/${id}`).then(r => r.json());
}

// ✅ Type-safe
async function getTournament(id: number): Promise<TournamentDTO> {
  return client.tournaments.get(id);
}
```

---

## Analytics & Statistics

### Decay

A mechanism where old performance data contributes less to current stats over time. Ensures recent matches have more weight.

**Used in:** Phase 3 (Advanced Stats), ELO calculation

**Example:**
```typescript
// Recent matches weighted more heavily
const decayFactor = 0.95; // 5% decay per day
const weightedELO = oldELO * Math.pow(decayFactor, daysSinceMatch);
```

---

### ELO Rating

A skill rating system where players gain/lose points based on match outcomes and opponent strength. Higher ELO = higher skill.

**Used in:** Phase 3 (Advanced Stats), leaderboards, matchmaking

**Example:**
```typescript
const stats = await client.analytics.getUserStats(userId, { game: gameId });
console.log('ELO:', stats.elo_rating); // e.g., 1650
```

---

### Leaderboard

A ranked list of users or teams ordered by performance metrics (ELO, wins, points).

**Types:**

- **Global User**: All users across all games
- **Global Team**: All teams across all games
- **Game User**: Users for a specific game
- **Game Team**: Teams for a specific game

**Used in:** Analytics dashboard, tournament pages

**Example:**
```typescript
const leaderboard = await client.leaderboards.get({
  type: 'game_user',
  game: gameId,
});
```

---

### Percentile

A statistical measure indicating the percentage of scores below a given value. Example: "You're in the 85th percentile" means you're better than 85% of players.

**Used in:** Analytics, user profiles

---

### Snapshot

A point-in-time capture of stats for historical tracking. Prevents stats from being retroactively changed.

**Used in:** Phase 3 (Advanced Stats), historical analysis

**Example:**
```typescript
// Monthly snapshot
{
  user_id: 123,
  game_id: 5,
  elo_rating: 1650,
  wins: 42,
  losses: 18,
  snapshot_date: '2025-06-01',
}
```

---

### Streak

Consecutive wins or losses. Tracked for analytics and achievements.

**Used in:** User profiles, analytics dashboard

**Example:**
```typescript
const stats = await client.analytics.getUserStats(userId);
console.log('Win streak:', stats.current_win_streak);
```

---

### Tier

A skill bracket grouping players by ELO range. Common tiers:

- **Bronze**: 0–999
- **Silver**: 1000–1499
- **Gold**: 1500–1999
- **Platinum**: 2000–2499
- **Diamond**: 2500+

**Used in:** Eligibility checks, matchmaking, leaderboards

**Example:**
```typescript
const { is_eligible, reasons } = await client.registration.checkEligibility({
  tournament_id: tournamentId,
});
// reasons: ['User tier (Bronze) below minimum (Gold)']
```

---

### Volatility

A measure of how much a player's rating fluctuates. High volatility = inconsistent performance.

**Used in:** Phase 3 (Advanced Stats), matchmaking confidence

---

## Developer Workflow

### Build

The process of compiling TypeScript, bundling JavaScript/CSS, and optimizing assets for deployment.

**Used in:** CI/CD, local development

**Example:**
```powershell
pnpm build
```

**Output:** `.next/` directory with production-ready code.

---

### CI/CD (Continuous Integration / Continuous Deployment)

Automated pipeline for testing, building, and deploying code. Steps:

1. **CI**: Run tests, lint, type-check on every commit
2. **CD**: Deploy to staging/production on merge to main

**Used in:** GitHub Actions, deployment workflow

---

### Dev Environment

Local development setup with hot reload, source maps, and debug tools.

**Used in:** Daily development

**Example:**
```powershell
pnpm dev # Start dev server
```

---

### Environment Variables

Configuration values that vary by environment (dev, staging, production). Examples:

- `NEXT_PUBLIC_API_BASE_URL`: Backend API URL
- `DATABASE_URL`: Database connection (backend)

**Used in:** `.env.local`, configuration

**Example:**
```bash
# .env.local
NEXT_PUBLIC_API_BASE_URL=https://api-staging.deltacrown.example.com
```

---

### Linting

Static code analysis to catch errors, enforce style, and maintain consistency. Uses **ESLint** for TypeScript/React.

**Used in:** Pre-commit hooks, CI/CD

**Example:**
```powershell
pnpm lint
pnpm lint --fix # Auto-fix issues
```

---

### Production Environment

The live environment serving real users. Characteristics:

- Optimized builds (minified, compressed)
- No debug tools
- Performance monitoring enabled

**Used in:** Deployment

---

### Staging Environment

A pre-production environment for testing changes before live deployment. Mirrors production setup.

**Used in:** QA, final testing

**Example:**
```bash
NEXT_PUBLIC_API_BASE_URL=https://api-staging.deltacrown.example.com
```

---

### Type Checking

Running the TypeScript compiler to verify type correctness without generating output.

**Used in:** CI/CD, pre-commit validation

**Example:**
```powershell
pnpm tsc --noEmit
```

---

## Additional Resources

For more detailed explanations and code examples, see:

- **Architecture Overview**: [INTRODUCTION.md](./INTRODUCTION.md)
- **Project Structure**: [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)
- **SDK Documentation**: [SDK_USAGE_GUIDE.md](./SDK_USAGE_GUIDE.md)
- **API Reference**: [API_REFERENCE.md](./API_REFERENCE.md)
- **Component Library**: [COMPONENTS_GUIDE.md](./COMPONENTS_GUIDE.md)

---

**Last Updated**: December 10, 2025
