# API Reference

## Table of Contents

1. [Introduction](#introduction)
2. [How to Read This Reference](#how-to-read-this-reference)
3. [Authentication & Authorization](#authentication--authorization)
4. [Auth & Profile](#auth--profile)
5. [Tournaments](#tournaments)
6. [Matches & Scheduling](#matches--scheduling)
7. [Registration & Smart Registration](#registration--smart-registration)
8. [Results & Disputes](#results--disputes)
9. [Staff & Referees](#staff--referees)
10. [Stats & Analytics](#stats--analytics)
11. [Match History](#match-history)
12. [Leaderboards](#leaderboards)
13. [Error Responses](#error-responses)
14. [Rate Limiting](#rate-limiting)

---

## Introduction

This is a **frontend-focused** API reference for the DeltaCrown Organizer Console. It documents the most important endpoints that the frontend interacts with, organized by domain.

**This is NOT the authoritative source of truth.** The complete API specification is available at:

```
/api/schema/
```

This reference exists to help frontend developers:

- Quickly find the endpoints they need
- Understand authentication requirements
- See SDK usage patterns at a glance

For detailed request/response schemas, parameter validation rules, and comprehensive API documentation, always refer to the **OpenAPI schema** exposed by the backend.

---

## How to Read This Reference

Each endpoint is documented with:

- **Method + URL**: The HTTP method and path
- **Description**: What the endpoint does (1–2 lines)
- **Auth**: Required authentication/authorization level
- **SDK Example**: TypeScript code showing how to call this endpoint using the DeltaCrown SDK

**Authentication Levels:**

- 🔓 **Public**: No authentication required
- 🔐 **Authenticated**: Any logged-in user
- 👔 **Organizer**: Tournament organizer role required
- 🎯 **Staff**: Staff or referee role required
- ⚙️ **Admin**: Admin role required

**SDK Reference:**

All examples assume you have initialized the SDK client:

```typescript
import { DeltaCrownClient } from '@/lib/sdk';

const client = new DeltaCrownClient({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL,
});
```

See [SDK_USAGE_GUIDE.md](./SDK_USAGE_GUIDE.md) for complete SDK documentation.

---

## Authentication & Authorization

### Overview

DeltaCrown uses **JWT-based authentication**. The frontend receives a token after login and includes it in subsequent requests via the `Authorization` header:

```
Authorization: Bearer <token>
```

The SDK handles this automatically when you configure it with the token (see [SDK_USAGE_GUIDE.md](./SDK_USAGE_GUIDE.md#authentication)).

**Role-Based Access Control (RBAC):**

Different endpoints require different roles:

- **Organizer**: Can create/manage tournaments, view organizer-specific dashboards
- **Staff/Referee**: Can manage matches, approve results, resolve disputes
- **Player**: Can register for tournaments, view match history
- **Admin**: Full system access (not covered in this frontend guide)

If a user lacks the required role, the API returns `403 Forbidden`.

---

## Auth & Profile

### Login

**`POST /api/auth/v1/login/`**

Authenticate a user and receive a JWT token.

- **Auth**: 🔓 Public
- **Description**: Exchange username/password for access token

**SDK Example:**

```typescript
// Note: Login is typically handled by AuthProvider, not called directly
const response = await fetch('/api/auth/v1/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username, password }),
});
const { access, refresh } = await response.json();
```

---

### Get Current User Profile

**`GET /api/auth/v1/profile/`**

Retrieve the authenticated user's profile.

- **Auth**: 🔐 Authenticated
- **Description**: Get current user details (username, email, roles)

**SDK Example:**

```typescript
const user = await client.auth.getCurrentUser();
console.log(user.username, user.roles);
```

---

### Update Profile

**`PATCH /api/auth/v1/profile/`**

Update the authenticated user's profile.

- **Auth**: 🔐 Authenticated
- **Description**: Update email, display name, avatar, etc.

**SDK Example:**

```typescript
await client.auth.updateProfile({
  display_name: 'New Name',
  avatar_url: 'https://example.com/avatar.jpg',
});
```

---

## Tournaments

### List Tournaments (Organizer)

**`GET /api/tournaments/v1/organizer/tournaments/`**

List all tournaments created by the authenticated organizer.

- **Auth**: 👔 Organizer
- **Description**: Retrieve tournaments with filtering, pagination, sorting

**Query Parameters:**

- `status`: Filter by status (draft, registration_open, in_progress, completed, cancelled)
- `game`: Filter by game ID
- `search`: Search by name
- `page`, `page_size`: Pagination

**SDK Example:**

```typescript
const tournaments = await client.tournaments.list({
  status: 'in_progress',
  game: gameId,
  page: 1,
  page_size: 20,
});
```

---

### Get Tournament Details

**`GET /api/tournaments/v1/organizer/tournaments/{id}/`**

Get detailed information about a specific tournament.

- **Auth**: 👔 Organizer (must own tournament)
- **Description**: Full tournament data including bracket, stages, schedule

**SDK Example:**

```typescript
const tournament = await client.tournaments.get(tournamentId);
console.log(tournament.name, tournament.status, tournament.bracket_type);
```

---

### Create Tournament

**`POST /api/tournaments/v1/organizer/tournaments/`**

Create a new tournament.

- **Auth**: 👔 Organizer
- **Description**: Create a tournament with basic configuration

**SDK Example:**

```typescript
const tournament = await client.tournaments.create({
  name: 'Summer Championship 2025',
  game: gameId,
  bracket_type: 'single_elimination',
  max_participants: 32,
  registration_start: '2025-06-01T00:00:00Z',
  registration_end: '2025-06-15T23:59:59Z',
  start_date: '2025-06-20T10:00:00Z',
});
```

---

### Update Tournament

**`PATCH /api/tournaments/v1/organizer/tournaments/{id}/`**

Update tournament configuration.

- **Auth**: 👔 Organizer (must own tournament)
- **Description**: Modify tournament settings (name, dates, prize pool, etc.)

**SDK Example:**

```typescript
await client.tournaments.update(tournamentId, {
  prize_pool: '5000.00',
  status: 'registration_open',
});
```

---

### Delete Tournament

**`DELETE /api/tournaments/v1/organizer/tournaments/{id}/`**

Delete a tournament.

- **Auth**: 👔 Organizer (must own tournament)
- **Description**: Soft-delete tournament (only allowed if no matches played)

**SDK Example:**

```typescript
await client.tournaments.delete(tournamentId);
```

---

### Get Tournament Leaderboard

**`GET /api/tournaments/v1/tournaments/{id}/leaderboard/`**

Get the leaderboard for a tournament.

- **Auth**: 🔓 Public
- **Description**: Ranked list of participants with wins, losses, points

**SDK Example:**

```typescript
const leaderboard = await client.tournaments.getLeaderboard(tournamentId);
leaderboard.forEach((entry) => {
  console.log(entry.rank, entry.player_name, entry.wins, entry.losses);
});
```

---

### Get Tournament Matches

**`GET /api/tournaments/v1/tournaments/{id}/matches/`**

Get all matches for a tournament.

- **Auth**: 🔓 Public
- **Description**: List matches with filtering by round, status

**SDK Example:**

```typescript
const matches = await client.tournaments.getMatches(tournamentId, {
  status: 'scheduled',
  round: 'semifinals',
});
```

---

## Matches & Scheduling

### List Matches (Organizer)

**`GET /api/matches/v1/organizer/matches/`**

List all matches for the organizer's tournaments.

- **Auth**: 👔 Organizer
- **Description**: Matches across all tournaments with filtering

**Query Parameters:**

- `tournament`: Filter by tournament ID
- `status`: Filter by status (scheduled, in_progress, completed, cancelled)
- `participant`: Filter by participant ID

**SDK Example:**

```typescript
const matches = await client.matches.list({
  tournament: tournamentId,
  status: 'scheduled',
});
```

---

### Get Match Details

**`GET /api/matches/v1/matches/{id}/`**

Get detailed information about a specific match.

- **Auth**: 🔓 Public
- **Description**: Full match data including participants, score, schedule

**SDK Example:**

```typescript
const match = await client.matches.get(matchId);
console.log(match.participant_1_name, match.participant_2_name, match.score);
```

---

### Update Match Score

**`PATCH /api/matches/v1/organizer/matches/{id}/score/`**

Update the score for a match.

- **Auth**: 👔 Organizer or 🎯 Staff
- **Description**: Submit match results

**SDK Example:**

```typescript
await client.matches.updateScore(matchId, {
  participant_1_score: 3,
  participant_2_score: 1,
  status: 'completed',
  winner: participant1Id,
});
```

---

### Get Scheduling Calendar

**`GET /api/scheduling/v1/organizer/calendar/`**

Get scheduling calendar view for the organizer.

- **Auth**: 👔 Organizer
- **Description**: Matches grouped by date/time for scheduling dashboard

**Query Parameters:**

- `tournament`: Filter by tournament ID
- `start_date`, `end_date`: Date range

**SDK Example:**

```typescript
const calendar = await client.scheduling.getCalendar({
  tournament: tournamentId,
  start_date: '2025-06-20',
  end_date: '2025-06-27',
});
```

---

### Schedule Match

**`POST /api/scheduling/v1/organizer/schedule-match/`**

Schedule a match with date, time, and venue.

- **Auth**: 👔 Organizer or 🎯 Staff
- **Description**: Assign schedule details to an unscheduled match

**SDK Example:**

```typescript
await client.scheduling.scheduleMatch({
  match_id: matchId,
  scheduled_time: '2025-06-21T14:00:00Z',
  venue: 'Arena 1',
});
```

---

### Bulk Schedule Matches

**`POST /api/scheduling/v1/organizer/bulk-schedule/`**

Schedule multiple matches at once.

- **Auth**: 👔 Organizer or 🎯 Staff
- **Description**: Schedule an array of matches in one request

**SDK Example:**

```typescript
await client.scheduling.bulkSchedule({
  schedules: [
    { match_id: match1Id, scheduled_time: '2025-06-21T14:00:00Z', venue: 'Arena 1' },
    { match_id: match2Id, scheduled_time: '2025-06-21T16:00:00Z', venue: 'Arena 2' },
  ],
});
```

---

## Registration & Smart Registration

### Check Eligibility

**`POST /api/registration/v1/check-eligibility/`**

Check if a user is eligible to register for a tournament.

- **Auth**: 🔐 Authenticated
- **Description**: Validates tier, rank, team requirements, blacklist status

**SDK Example:**

```typescript
const eligibility = await client.registration.checkEligibility({
  tournament_id: tournamentId,
});

if (!eligibility.is_eligible) {
  console.error('Not eligible:', eligibility.reasons);
}
```

---

### Create Registration

**`POST /api/registration/v1/register/`**

Register for a tournament.

- **Auth**: 🔐 Authenticated
- **Description**: Create registration record (pending payment if entry fee > 0)

**SDK Example:**

```typescript
const registration = await client.registration.create({
  tournament_id: tournamentId,
  game_identity: userGameIdentity,
});

if (registration.payment_required) {
  // Redirect to payment flow
  window.location.href = `/payment/${registration.payment_id}`;
}
```

---

### Withdraw from Tournament

**`DELETE /api/registration/v1/registrations/{id}/`**

Withdraw from a tournament.

- **Auth**: 🔐 Authenticated (must own registration)
- **Description**: Cancel registration (may have refund logic)

**SDK Example:**

```typescript
await client.registration.withdraw(registrationId);
```

---

### List Registrations (Organizer)

**`GET /api/registration/v1/organizer/registrations/`**

List all registrations for the organizer's tournaments.

- **Auth**: 👔 Organizer
- **Description**: View registrations with filtering by tournament, status

**SDK Example:**

```typescript
const registrations = await client.registration.list({
  tournament: tournamentId,
  status: 'confirmed',
});
```

---

## Results & Disputes

### Get Pending Results (Organizer)

**`GET /api/tournaments/v1/organizer/results-inbox/`**

Get all pending match results awaiting approval.

- **Auth**: 👔 Organizer or 🎯 Staff
- **Description**: Results inbox for staff to review and approve

**SDK Example:**

```typescript
const pending = await client.results.getPending({ tournament: tournamentId });
console.log(`${pending.length} results pending approval`);
```

---

### Approve Result

**`POST /api/results/v1/organizer/approve/{result_id}/`**

Approve a submitted match result.

- **Auth**: 👔 Organizer or 🎯 Staff
- **Description**: Mark result as approved, update leaderboard

**SDK Example:**

```typescript
await client.results.approve(resultId);
```

---

### Reject Result

**`POST /api/results/v1/organizer/reject/{result_id}/`**

Reject a submitted match result.

- **Auth**: 👔 Organizer or 🎯 Staff
- **Description**: Reject result with reason, request resubmission

**SDK Example:**

```typescript
await client.results.reject(resultId, {
  reason: 'Score does not match video evidence',
});
```

---

### Create Dispute

**`POST /api/disputes/v1/create/`**

Create a dispute for a match result.

- **Auth**: 🔐 Authenticated (participant in match)
- **Description**: Challenge match result with evidence

**SDK Example:**

```typescript
await client.disputes.create({
  match_id: matchId,
  reason: 'Opponent used banned character',
  description: 'Detailed explanation...',
  evidence_urls: ['https://example.com/video.mp4'],
});
```

---

### List Disputes (Organizer)

**`GET /api/disputes/v1/organizer/disputes/`**

List all disputes for the organizer's tournaments.

- **Auth**: 👔 Organizer or 🎯 Staff
- **Description**: View disputes with filtering by status, tournament

**SDK Example:**

```typescript
const disputes = await client.disputes.list({
  tournament: tournamentId,
  status: 'pending',
});
```

---

### Resolve Dispute

**`POST /api/disputes/v1/organizer/resolve/{dispute_id}/`**

Resolve a dispute.

- **Auth**: 👔 Organizer or 🎯 Staff
- **Description**: Accept, reject, or modify match result based on dispute

**SDK Example:**

```typescript
await client.disputes.resolve(disputeId, {
  resolution: 'accepted',
  notes: 'Evidence confirms violation',
  action: 'reverse_result',
});
```

---

## Staff & Referees

### List Staff (Organizer)

**`GET /api/staff/v1/organizer/staff/`**

List all staff for the organizer's tournaments.

- **Auth**: 👔 Organizer
- **Description**: View staff members with roles and permissions

**SDK Example:**

```typescript
const staff = await client.staff.list({ tournament: tournamentId });
staff.forEach((member) => {
  console.log(member.user_name, member.role, member.permissions);
});
```

---

### Add Staff

**`POST /api/staff/v1/organizer/staff/`**

Add a staff member to a tournament.

- **Auth**: 👔 Organizer
- **Description**: Assign user as staff/referee with permissions

**SDK Example:**

```typescript
await client.staff.add({
  tournament_id: tournamentId,
  user_id: userId,
  role: 'referee',
  permissions: ['approve_results', 'schedule_matches'],
});
```

---

### Update Staff Permissions

**`PATCH /api/staff/v1/organizer/staff/{id}/permissions/`**

Update staff member's permissions.

- **Auth**: 👔 Organizer
- **Description**: Modify permission set for staff member

**SDK Example:**

```typescript
await client.staff.updatePermissions(staffId, {
  permissions: ['approve_results', 'resolve_disputes', 'schedule_matches'],
});
```

---

### Remove Staff

**`DELETE /api/staff/v1/organizer/staff/{id}/`**

Remove a staff member from a tournament.

- **Auth**: 👔 Organizer
- **Description**: Revoke staff access

**SDK Example:**

```typescript
await client.staff.remove(staffId);
```

---

## Stats & Analytics

### Get Organizer Dashboard

**`GET /api/analytics/v1/organizer/dashboard/`**

Get organizer dashboard metrics.

- **Auth**: 👔 Organizer
- **Description**: High-level stats (active tournaments, revenue, participants)

**SDK Example:**

```typescript
const dashboard = await client.analytics.getOrganizerDashboard();
console.log('Active tournaments:', dashboard.active_tournaments);
console.log('Total participants:', dashboard.total_participants);
console.log('Revenue (30d):', dashboard.revenue_30d);
```

---

### Get User Stats

**`GET /api/stats/v1/users/{user_id}/stats/`**

Get statistics for a specific user.

- **Auth**: 🔐 Authenticated
- **Description**: Win/loss record, ELO, tier, match count

**SDK Example:**

```typescript
const stats = await client.analytics.getUserStats(userId, { game: gameId });
console.log('W-L:', stats.wins, stats.losses);
console.log('ELO:', stats.elo_rating);
console.log('Tier:', stats.tier);
```

---

### Get Team Stats

**`GET /api/stats/v1/teams/{team_id}/stats/`**

Get statistics for a team.

- **Auth**: 🔐 Authenticated
- **Description**: Team performance metrics across games

**SDK Example:**

```typescript
const stats = await client.analytics.getTeamStats(teamId, { game: gameId });
console.log('Team ELO:', stats.elo_rating);
console.log('Total matches:', stats.total_matches);
```

---

## Match History

### Get User Match History

**`GET /api/match-history/v1/users/{user_id}/history/`**

Get match history for a user.

- **Auth**: 🔐 Authenticated
- **Description**: Paginated list of past matches with results

**Query Parameters:**

- `game`: Filter by game ID
- `result`: Filter by result (win, loss, draw)
- `page`, `page_size`: Pagination

**SDK Example:**

```typescript
const history = await client.matchHistory.getUserHistory(userId, {
  game: gameId,
  result: 'win',
  page: 1,
  page_size: 20,
});
```

---

### Get Team Match History

**`GET /api/match-history/v1/teams/{team_id}/history/`**

Get match history for a team.

- **Auth**: 🔐 Authenticated
- **Description**: Team's match history with filtering

**SDK Example:**

```typescript
const history = await client.matchHistory.getTeamHistory(teamId, {
  game: gameId,
});
```

---

## Leaderboards

### Get Leaderboard

**`GET /api/leaderboards/v1/leaderboards/`**

Get global or game-specific leaderboard.

- **Auth**: 🔓 Public
- **Description**: Ranked list of users or teams

**Query Parameters:**

- `type`: `global_user`, `global_team`, `game_user`, `game_team`
- `game`: Game ID (required if type is game-specific)
- `page`, `page_size`: Pagination

**SDK Example:**

```typescript
const leaderboard = await client.leaderboards.get({
  type: 'game_user',
  game: gameId,
  page: 1,
  page_size: 50,
});

leaderboard.results.forEach((entry) => {
  console.log(entry.rank, entry.player_name, entry.elo_rating);
});
```

---

## Error Responses

All API endpoints return consistent error responses:

```typescript
{
  "detail": "Human-readable error message",
  "code": "ERROR_CODE", // Optional, for specific error types
  "errors": { // Optional, for validation errors
    "field_name": ["Error message for this field"]
  }
}
```

**Common HTTP Status Codes:**

- `400 Bad Request`: Invalid request data (validation errors)
- `401 Unauthorized`: Missing or invalid authentication token
- `403 Forbidden`: Authenticated but lacking required permissions
- `404 Not Found`: Resource does not exist
- `409 Conflict`: Request conflicts with current state (e.g., duplicate registration)
- `422 Unprocessable Entity`: Business logic validation failed
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Unexpected server error

**SDK Error Handling:**

The SDK wraps API errors in an `ApiError` class:

```typescript
import { ApiError } from '@/lib/sdk';

try {
  await client.tournaments.create(data);
} catch (error) {
  if (error instanceof ApiError) {
    console.error('API Error:', error.status, error.message);
    console.error('Details:', error.data);
  }
}
```

See [SDK_USAGE_GUIDE.md#error-handling](./SDK_USAGE_GUIDE.md#error-handling) for complete error handling patterns.

---

## Rate Limiting

DeltaCrown implements rate limiting to prevent abuse. Rate limit headers are included in responses:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1623456789
```

**Default Limits:**

- **Authenticated users**: 1000 requests/hour
- **Unauthenticated**: 100 requests/hour
- **Organizer endpoints**: 2000 requests/hour

If you exceed the rate limit, the API returns `429 Too Many Requests` with a `Retry-After` header.

**Best Practices:**

- Cache responses where possible (tournaments, leaderboards)
- Use polling intervals wisely (don't poll every second)
- Batch operations when available (e.g., bulk schedule)
- Respect `Retry-After` header if rate limited

---

## Additional Resources

- **OpenAPI Schema**: `/api/schema/` (authoritative source)
- **SDK Usage Guide**: [SDK_USAGE_GUIDE.md](./SDK_USAGE_GUIDE.md)
- **Workflow Examples**: [WORKFLOW_GUIDE.md](./WORKFLOW_GUIDE.md)
- **Component Library**: [COMPONENTS_GUIDE.md](./COMPONENTS_GUIDE.md)

For questions or issues, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).
