# DeltaCrown SDK

TypeScript SDK for DeltaCrown Tournament Platform API.

**Epic:** Phase 9, Epic 9.2 - JSON Schemas & TypeScript Types

## Overview

Fully typed SDK providing IntelliSense support and compile-time type safety for all DeltaCrown APIs.

- **Generated Types**: 78 TypeScript interfaces auto-generated from OpenAPI 3.0 schema
- **Domain Types**: Hand-curated types organized by feature area (10+ domains)
- **Typed Client**: Methods for all major API endpoints with full type inference
- **Framework Agnostic**: Works with any JavaScript/TypeScript frontend

## Installation

```bash
# Using pnpm (recommended)
pnpm install @deltacrown/sdk

# Using npm
npm install @deltacrown/sdk

# Using yarn
yarn add @deltacrown/sdk
```

## Quick Start

```typescript
import { DeltaCrownClient } from '@deltacrown/sdk';

// Create client
const client = new DeltaCrownClient({
  baseUrl: 'https://api.deltacrown.gg',
});

// Authenticate
const { access, refresh } = await client.obtainToken('username', 'password');
client.setAccessToken(access);

// Get tournaments
const tournaments = await client.getTournaments({
  status: 'registration_open',
  game_slug: 'league-of-legends',
});

// Register for tournament
await client.register(tournamentId, {
  tournament_id: tournamentId,
  participant_type: 'user',
  participant_id: userId,
  game_identity_fields: {
    summoner_name: 'TheLegend27',
    region: 'NA',
  },
  agreed_to_rules: true,
});
```

## Client Configuration

```typescript
const client = new DeltaCrownClient({
  baseUrl: 'https://api.deltacrown.gg',  // API base URL
  accessToken: 'eyJ0eXAi...',             // Optional: pre-set auth token
  onUnauthorized: () => {                 // Optional: 401 handler
    console.log('Session expired');
    window.location.href = '/login';
  },
  onError: (error) => {                   // Optional: global error handler
    console.error(`API Error: ${error.message}`);
  },
});
```

## API Coverage

### Authentication
- `obtainToken(username, password)` - Get JWT access/refresh tokens
- `refreshToken(refreshToken)` - Refresh access token
- `setAccessToken(token)` - Set authentication token
- `clearAccessToken()` - Clear authentication token

### Registration
- `register(tournamentId, form)` - Register for tournament
- `getRegistrations(tournamentId)` - List registrations
- `getRegistration(registrationId)` - Get registration details
- `cancelRegistration(registrationId)` - Cancel registration
- `checkEligibility(tournamentId, participantType, participantId)` - Check eligibility

### Tournaments
- `getTournaments(filters?)` - List tournaments with filters
- `getTournament(tournamentId)` - Get tournament details
- `getMyTournaments()` - Get current user's tournaments

### Matches
- `getMatch(matchId)` - Get match details
- `submitResult(matchId, data)` - Submit match result
- `confirmResult(matchId)` - Confirm opponent's result

### Disputes
- `createDispute(matchId, reason, evidence?)` - File dispute
- `getDispute(disputeId)` - Get dispute details

### Organizer - Results Inbox
- `getOrganizerResultsInbox(filters?)` - List pending results
- `bulkActionResultsInbox(data)` - Bulk finalize/reject results

### Organizer - Scheduling
- `getSchedulingItems(filters?)` - List matches to schedule
- `assignMatchSchedule(data)` - Schedule match
- `getAvailableSlots(tournamentId)` - Get available time slots

### Organizer - Staffing
- `getStaffMembers(tournamentId)` - List tournament staff
- `assignStaff(tournamentId, userId, role)` - Assign staff member
- `assignReferee(matchId, refereeId)` - Assign referee to match

### Organizer - MOCC (Match Operations)
- `executeMoccAction(data)` - Execute match control action
- `getMatchTimeline(matchId)` - Get match event timeline

### Organizer - Audit Logs
- `getAuditLogs(filters?)` - List audit log entries
- `getTournamentAuditTrail(tournamentId)` - Get tournament audit trail

### Stats & History
- `getUserStats(userId, gameSlug?)` - Get user stats
- `getTeamStats(teamId, gameSlug?)` - Get team stats
- `getUserMatchHistory(userId, params?)` - Get user match history
- `getTeamMatchHistory(teamId, params?)` - Get team match history

### Leaderboards
- `getLeaderboard(type, params?)` - Get leaderboard (7 types: global_user, game_user, team, seasonal, mmr, elo, tier)

### Seasons
- `getCurrentSeason(gameSlug?)` - Get current active season
- `getSeasons(params?)` - List all seasons

## Type System

### Generated Types
Auto-generated from OpenAPI schema (78 types):
```typescript
import type { 
  TournamentRead,
  RegistrationRead,
  MatchRead,
  // ... 75 more
} from '@deltacrown/sdk';
```

### Domain Types
Hand-curated, frontend-friendly types organized by domain:

**Registration Domain:**
```typescript
type RegistrationStatus = 'pending' | 'approved' | 'rejected' | 'waitlisted' | 'cancelled';
type PaymentStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'refunded';

interface RegistrationForm {
  tournament_id: number;
  participant_type: 'user' | 'team';
  participant_id: number;
  game_identity_fields: Record<string, any>;
  custom_fields?: Record<string, any>;
  documents?: Array<{ document_type: string; file_url: string }>;
  agreed_to_rules: boolean;
}
```

**Tournament Domain:**
```typescript
type TournamentFormat = 'single_elimination' | 'double_elimination' | 'round_robin' | 'swiss' | 'group_stage';
type TournamentStatus = 'draft' | 'published' | 'registration_open' | 'registration_closed' | 'check_in_open' | 'in_progress' | 'completed' | 'cancelled';

interface TournamentSummary {
  id: number;
  name: string;
  game_slug: string;
  format: TournamentFormat;
  status: TournamentStatus;
  // ... 7 more fields
}
```

**Match Domain:**
```typescript
type MatchStatus = 'scheduled' | 'check_in' | 'ready' | 'live' | 'awaiting_results' | 'results_submitted' | 'completed' | 'forfeit';

interface MatchSummary {
  id: number;
  status: MatchStatus;
  participant1_type: 'user' | 'team';
  participant1_id: number;
  // ... 10 more fields
}
```

**Stats Domain:**
```typescript
interface UserStatsSummary {
  user_id: number;
  game_slug: string;
  matches_played: number;
  matches_won: number;
  win_rate: number;
  current_streak: number;
  best_streak: number;
  // ... 7 more fields including elo, mmr, K/D/A
}
```

**Leaderboards:**
```typescript
type LeaderboardType = 'global_user' | 'game_user' | 'team' | 'seasonal' | 'mmr' | 'elo' | 'tier';

interface LeaderboardResponse {
  leaderboard_type: LeaderboardType;
  game_slug?: string;
  season_id?: string;
  total_entries: number;
  entries: LeaderboardRow[];
}
```

See `src/types.domain.ts` for complete domain type definitions (10+ domains).

### Common Types
```typescript
interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

interface ApiError {
  error: string;
  details?: Record<string, any>;
  status_code: number;
}

interface SuccessResponse {
  message: string;
  data?: any;
}
```

## Error Handling

```typescript
import { ApiError } from '@deltacrown/sdk';

try {
  const tournament = await client.getTournament(999);
} catch (error) {
  if (error instanceof ApiError) {
    console.error(`Error ${error.statusCode}: ${error.message}`);
    console.error('Details:', error.details);
  }
}

// Or use global error handler
const client = new DeltaCrownClient({
  onError: (error) => {
    showToast(`Error: ${error.message}`, 'error');
  },
});
```

## Type Safety Examples

### Tournament Filtering
```typescript
// TypeScript enforces valid enum values
const tournaments = await client.getTournaments({
  status: 'registration_open',  // ✅ Valid
  format: 'single_elimination',  // ✅ Valid
  // status: 'invalid_status',   // ❌ TypeScript error
});

// Type inference for response
tournaments.results.forEach(t => {
  console.log(t.name);           // ✅ Known property
  console.log(t.can_register);   // ✅ Known property
  // console.log(t.invalid);     // ❌ TypeScript error
});
```

### Match Result Submission
```typescript
// Form data is fully typed
await client.submitResult(matchId, {
  match_id: matchId,
  winner_type: 'user',           // ✅ 'user' | 'team'
  winner_id: 42,
  score: '2-1',
  result_data: {
    game_1_screenshot: 'https://...',
  },
  // winner_type: 'invalid',     // ❌ TypeScript error
});
```

### Organizer Bulk Actions
```typescript
const result = await client.bulkActionResultsInbox({
  submission_ids: [1, 2, 3],
  action: 'finalize',            // ✅ 'finalize' | 'reject'
  reason: 'Bulk approval',
  // action: 'invalid',          // ❌ TypeScript error
});

// Response is fully typed
console.log(result.success_count);
console.log(result.failed_count);
result.results.forEach(r => {
  console.log(r.submission_id, r.success, r.message);
});
```

## Regenerating Types

When backend API schema changes:

```bash
# 1. Regenerate OpenAPI schema (backend)
python manage.py spectacular --file schema.yml

# 2. Regenerate TypeScript types (frontend SDK)
cd frontend_sdk
pnpm run generate

# 3. Type check
pnpm run type-check

# 4. Review generated types
git diff src/types.generated.ts
```

## Development

```bash
# Install dependencies
pnpm install

# Generate types from OpenAPI schema
pnpm run generate

# Type check
pnpm run type-check

# Build SDK
pnpm run build
```

## Project Structure

```
frontend_sdk/
├── src/
│   ├── index.ts              # Main entry point
│   ├── client.ts             # DeltaCrownClient class (~440 LOC)
│   ├── endpoints.ts          # Endpoint path configuration (~280 LOC)
│   ├── types.domain.ts       # Hand-curated domain types (~570 LOC)
│   └── types.generated.ts    # Auto-generated types (78 types, ~1,500 LOC)
├── tests/
│   └── type-check.test.ts    # Type safety validation
├── tools/
│   └── generate_frontend_types.py  # OpenAPI → TypeScript generator
├── package.json
├── tsconfig.json
└── README.md
```

## Architecture

1. **Schema-Driven**: Types generated from authoritative OpenAPI 3.0 schema
2. **Layered Types**: Generated base types + curated domain types
3. **Centralized Endpoints**: Single source of truth for API paths
4. **Type-Safe Client**: Full IntelliSense and compile-time validation
5. **Framework Agnostic**: Works with any JS/TS frontend (React, Vue, Vanilla, HTMX)

## Integration Examples

### Vanilla JavaScript + HTMX
```typescript
import { DeltaCrownClient } from '@deltacrown/sdk';

const client = new DeltaCrownClient({ baseUrl: '/api' });

// Fetch tournaments and update DOM
async function loadTournaments() {
  const tournaments = await client.getTournaments({ status: 'registration_open' });
  
  const html = tournaments.results.map(t => `
    <div class="tournament-card">
      <h3>${t.name}</h3>
      <p>${t.current_participants} / ${t.max_participants} players</p>
      ${t.can_register ? '<button hx-post="/register">Register</button>' : ''}
    </div>
  `).join('');
  
  document.getElementById('tournaments').innerHTML = html;
}
```

### React + TypeScript
```typescript
import { DeltaCrownClient, TournamentSummary } from '@deltacrown/sdk';
import { useState, useEffect } from 'react';

const client = new DeltaCrownClient({ baseUrl: '/api' });

function TournamentList() {
  const [tournaments, setTournaments] = useState<TournamentSummary[]>([]);
  
  useEffect(() => {
    client.getTournaments({ status: 'registration_open' })
      .then(res => setTournaments(res.results));
  }, []);
  
  return (
    <div>
      {tournaments.map(t => (
        <div key={t.id}>
          <h3>{t.name}</h3>
          <p>{t.format} - {t.game_slug}</p>
        </div>
      ))}
    </div>
  );
}
```

## Support

- **Documentation**: See `docs/api/` in main repository
- **OpenAPI Schema**: Available at `/api/schema/` endpoint
- **Swagger UI**: Available at `/api/schema/swagger-ui/`
- **Issues**: Report bugs in main repository issue tracker

## License

Proprietary - DeltaCrown Tournament Platform

---

**Version:** 1.0.0  
**Epic:** Phase 9, Epic 9.2  
**Generated:** December 10, 2025
