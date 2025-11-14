# DeltaCrown API Endpoint Catalog

## Overview

Complete reference of all REST API and WebSocket endpoints in the DeltaCrown backend.

**Base URL**: `http://localhost:8000` (development)  
**Authentication**: JWT Bearer tokens  
**Content-Type**: `application/json`  

---

## Authentication Endpoints

### Obtain JWT Token
```http
POST /api/token/
Content-Type: application/json

{
  "username": "string",
  "password": "string"
}

Response 200:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Refresh JWT Token
```http
POST /api/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}

Response 200:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Verify JWT Token
```http
POST /api/token/verify/
Content-Type: application/json

{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}

Response 200: {}
Response 401: {"detail": "Token is invalid or expired"}
```

---

## Tournament Endpoints

### List Tournaments
```http
GET /api/tournaments/
Authorization: Bearer {access_token}

Query Parameters:
- status: DRAFT|PUBLISHED|LIVE|COMPLETED|CANCELLED
- game: valorant|efootball|fifa|csgo
- page: int (default: 1)
- page_size: int (default: 20)

Response 200:
{
  "count": 42,
  "next": "http://localhost:8000/api/tournaments/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Summer Championship 2025",
      "game": "valorant",
      "status": "LIVE",
      "organizer_id": 5,
      "tournament_start": "2025-07-01T10:00:00Z",
      "registration_end": "2025-06-15T23:59:59Z",
      "max_participants": 32,
      "total_registrations": 28,
      "prize_pool": "5000.00",
      "entry_fee_amount": "10.00"
    }
  ]
}
```

### Create Tournament
```http
POST /api/tournaments/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "string",
  "game": "valorant|efootball|fifa|csgo",
  "format": "SINGLE_ELIMINATION|DOUBLE_ELIMINATION|ROUND_ROBIN",
  "participation_type": "SOLO|TEAM",
  "tournament_start": "2025-12-01T10:00:00Z",
  "tournament_end": "2025-12-01T18:00:00Z",
  "registration_start": "2025-11-15T00:00:00Z",
  "registration_end": "2025-11-30T23:59:59Z",
  "max_participants": 32,
  "min_participants": 8,
  "entry_fee_amount": "10.00",
  "prize_pool": "500.00"
}

Response 201:
{
  "id": 123,
  "name": "string",
  "status": "DRAFT",
  ...
}
```

### Get Tournament Details
```http
GET /api/tournaments/{id}/
Authorization: Bearer {access_token}

Response 200:
{
  "id": 1,
  "name": "Summer Championship 2025",
  "game": "valorant",
  "status": "LIVE",
  "organizer_id": 5,
  "format": "SINGLE_ELIMINATION",
  "participation_type": "TEAM",
  "tournament_start": "2025-07-01T10:00:00Z",
  "tournament_end": "2025-07-01T20:00:00Z",
  "registration_start": "2025-06-01T00:00:00Z",
  "registration_end": "2025-06-15T23:59:59Z",
  "max_participants": 32,
  "min_participants": 8,
  "total_registrations": 28,
  "total_matches": 31,
  "completed_matches": 15,
  "prize_pool": "5000.00",
  "entry_fee_amount": "10.00",
  "created_at": "2025-05-01T12:00:00Z"
}
```

### Register for Tournament
```http
POST /api/tournaments/{id}/register/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "team_id": 123  // For team tournaments only
}

Response 201:
{
  "id": 456,
  "tournament_id": 1,
  "user_id": 789,
  "team_id": 123,
  "status": "PENDING_PAYMENT",
  "created_at": "2025-06-10T15:30:00Z"
}
```

### Check-in for Tournament
```http
POST /api/tournaments/{id}/check-in/
Authorization: Bearer {access_token}

Response 200:
{
  "id": 456,
  "status": "CHECKED_IN",
  "checked_in_at": "2025-07-01T09:45:00Z"
}
```

---

## Registration Endpoints

### List My Registrations
```http
GET /api/tournaments/registrations/
Authorization: Bearer {access_token}

Query Parameters:
- status: PENDING_PAYMENT|CONFIRMED|CHECKED_IN|CANCELLED
- tournament: int (tournament ID)

Response 200:
{
  "count": 5,
  "results": [
    {
      "id": 456,
      "tournament_id": 1,
      "user_id": 789,
      "team_id": 123,
      "status": "CONFIRMED",
      "created_at": "2025-06-10T15:30:00Z"
    }
  ]
}
```

### Get Registration Details
```http
GET /api/tournaments/registrations/{id}/
Authorization: Bearer {access_token}

Response 200:
{
  "id": 456,
  "tournament_id": 1,
  "user_id": 789,
  "team_id": 123,
  "status": "CONFIRMED",
  "payment_verified": true,
  "checked_in_at": null,
  "created_at": "2025-06-10T15:30:00Z"
}
```

### Cancel Registration
```http
DELETE /api/tournaments/registrations/{id}/
Authorization: Bearer {access_token}

Response 204: No Content
```

---

## Team Endpoints

### List Teams
```http
GET /api/teams/
Authorization: Bearer {access_token}

Query Parameters:
- game: valorant|efootball|fifa|csgo
- search: string (team name)

Response 200:
{
  "count": 10,
  "results": [
    {
      "id": 123,
      "name": "Team Alpha",
      "tag": "TMA",
      "game": "valorant",
      "captain_id": 456,
      "member_count": 5,
      "created_at": "2025-05-15T12:00:00Z"
    }
  ]
}
```

### Create Team
```http
POST /api/teams/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "string",
  "tag": "string (3-5 chars)",
  "game": "valorant|efootball|fifa|csgo",
  "description": "string"
}

Response 201:
{
  "id": 123,
  "name": "Team Alpha",
  "tag": "TMA",
  "game": "valorant",
  "captain_id": 456,
  "created_at": "2025-05-15T12:00:00Z"
}
```

### Get Team Details
```http
GET /api/teams/{id}/
Authorization: Bearer {access_token}

Response 200:
{
  "id": 123,
  "name": "Team Alpha",
  "tag": "TMA",
  "game": "valorant",
  "captain_id": 456,
  "member_ids": [456, 789, 101],
  "member_count": 3,
  "created_at": "2025-05-15T12:00:00Z"
}
```

### Invite Team Member
```http
POST /api/teams/{id}/invite/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "user_id": 789
}

Response 201:
{
  "id": 999,
  "team_id": 123,
  "user_id": 789,
  "status": "PENDING"
}
```

### Accept Team Invitation
```http
POST /api/teams/{team_id}/invitations/{invitation_id}/accept/
Authorization: Bearer {access_token}

Response 200:
{
  "id": 999,
  "status": "ACCEPTED"
}
```

---

## Match Endpoints

### List Tournament Matches
```http
GET /api/tournaments/{tournament_id}/matches/
Authorization: Bearer {access_token}

Query Parameters:
- state: PENDING|IN_PROGRESS|COMPLETED|CANCELLED
- round: int

Response 200:
{
  "count": 15,
  "results": [
    {
      "id": 501,
      "tournament_id": 1,
      "round": 1,
      "match_number": 1,
      "state": "COMPLETED",
      "participant1_id": 123,
      "participant2_id": 456,
      "winner_id": 123,
      "score": {"team1": 13, "team2": 8},
      "scheduled_at": "2025-07-01T10:00:00Z",
      "completed_at": "2025-07-01T11:30:00Z"
    }
  ]
}
```

### Get Match Details
```http
GET /api/matches/{id}/
Authorization: Bearer {access_token}

Response 200:
{
  "id": 501,
  "tournament_id": 1,
  "round": 1,
  "match_number": 1,
  "state": "COMPLETED",
  "participant1_id": 123,
  "participant2_id": 456,
  "team1_id": 123,
  "team2_id": 456,
  "winner_id": 123,
  "score": {"team1": 13, "team2": 8},
  "scheduled_at": "2025-07-01T10:00:00Z",
  "started_at": "2025-07-01T10:05:00Z",
  "completed_at": "2025-07-01T11:30:00Z"
}
```

### Report Match Score (Organizer only)
```http
POST /api/matches/{id}/report-score/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "winner_id": 123,
  "score": {"team1": 13, "team2": 8}
}

Response 200:
{
  "id": 501,
  "state": "COMPLETED",
  "winner_id": 123,
  "score": {"team1": 13, "team2": 8}
}
```

---

## Leaderboard Endpoints

### Get Global Leaderboard
```http
GET /api/leaderboards/
Authorization: Bearer {access_token}

Query Parameters:
- game: valorant|efootball|fifa|csgo
- period: ALL_TIME|MONTHLY|WEEKLY
- page: int

Response 200:
{
  "count": 100,
  "results": [
    {
      "rank": 1,
      "user_id": 456,
      "username": "ProPlayer123",
      "game": "valorant",
      "rating": 2500,
      "wins": 45,
      "losses": 12,
      "tournaments_played": 8
    }
  ]
}
```

### Get Tournament Leaderboard
```http
GET /api/tournaments/{id}/leaderboard/
Authorization: Bearer {access_token}

Response 200:
{
  "tournament_id": 1,
  "entries": [
    {
      "rank": 1,
      "participant_id": 123,
      "team_id": 123,
      "wins": 4,
      "losses": 0,
      "points": 12,
      "rounds_won": 52,
      "rounds_lost": 24
    }
  ]
}
```

---

## Economy Endpoints

### Get Wallet Balance
```http
GET /api/economy/wallet/
Authorization: Bearer {access_token}

Response 200:
{
  "user_id": 789,
  "balance": "1500.00",
  "pending": "50.00",
  "currency": "deltacoin"
}
```

### List Transactions
```http
GET /api/economy/transactions/
Authorization: Bearer {access_token}

Query Parameters:
- type: DEPOSIT|WITHDRAWAL|TRANSFER|ENTRY_FEE|PRIZE
- page: int

Response 200:
{
  "count": 25,
  "results": [
    {
      "id": "txn_abc123",
      "type": "ENTRY_FEE",
      "amount": "-10.00",
      "balance_after": "1490.00",
      "description": "Tournament entry fee",
      "created_at": "2025-06-10T15:30:00Z"
    }
  ]
}
```

---

## Health Check Endpoints

### Liveness Check
```http
GET /healthz/
No authentication required

Response 200:
{
  "status": "ok",
  "service": "deltacrown"
}
```

### Readiness Check
```http
GET /readiness/
No authentication required

Response 200:
{
  "status": "ready",
  "checks": {
    "database": true,
    "cache": true
  }
}

Response 503 (if unhealthy):
{
  "status": "not_ready",
  "checks": {
    "database": false,
    "cache": true
  }
}
```

---

## WebSocket Endpoints

### Tournament Updates
```
ws://localhost:8000/ws/tournaments/{tournament_id}/
Authorization: Bearer {access_token} (in query or header)

Message Types (Server → Client):
{
  "type": "tournament.status_update",
  "data": {
    "tournament_id": 1,
    "status": "LIVE"
  }
}

{
  "type": "tournament.registration_update",
  "data": {
    "tournament_id": 1,
    "total_registrations": 29
  }
}
```

### Match Updates
```
ws://localhost:8000/ws/matches/{match_id}/
Authorization: Bearer {access_token}

Message Types (Server → Client):
{
  "type": "match.state_update",
  "data": {
    "match_id": 501,
    "state": "IN_PROGRESS"
  }
}

{
  "type": "match.score_update",
  "data": {
    "match_id": 501,
    "score": {"team1": 10, "team2": 8}
  }
}

{
  "type": "match.completed",
  "data": {
    "match_id": 501,
    "winner_id": 123,
    "final_score": {"team1": 13, "team2": 8}
  }
}
```

### Bracket Updates
```
ws://localhost:8000/ws/tournaments/{tournament_id}/bracket/
Authorization: Bearer {access_token}

Message Types (Server → Client):
{
  "type": "bracket.updated",
  "data": {
    "tournament_id": 1,
    "round": 2,
    "matches_generated": 8
  }
}
```

---

## Error Responses

All errors follow consistent format (Module 9.5):

```json
{
  "error": "Human-readable error message",
  "code": "ERROR_CODE",
  "details": {
    "field": ["Error detail"]
  }
}
```

### Common Error Codes

- `UNAUTHENTICATED` (401) - Authentication required
- `AUTHENTICATION_FAILED` (401) - Invalid credentials
- `PERMISSION_DENIED` (403) - Insufficient permissions
- `NOT_FOUND` (404) - Resource not found
- `VALIDATION_ERROR` (400) - Invalid request data
- `RATE_LIMITED` (429) - Rate limit exceeded
- `INTEGRITY_ERROR` (409) - Database constraint violation
- `INTERNAL_ERROR` (500) - Server error

---

## Rate Limits

- **Anonymous**: 100 requests/hour
- **Authenticated**: 1000 requests/hour
- **WebSocket**: Connection limits per user

Headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1625097600
```

---

## Pagination

All list endpoints use cursor pagination:

```json
{
  "count": 100,
  "next": "http://localhost:8000/api/resource/?page=2",
  "previous": null,
  "results": [...]
}
```

Query parameters:
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20, max: 100)

---

## Filtering & Search

Most list endpoints support:
- **Filtering**: `?status=LIVE&game=valorant`
- **Search**: `?search=championship`
- **Ordering**: `?ordering=-created_at` (- for descending)

---

## Testing Endpoints

Use curl or Postman:

```bash
# Get token
TOKEN=$(curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' \
  | jq -r '.access')

# Use token
curl http://localhost:8000/api/tournaments/ \
  -H "Authorization: Bearer $TOKEN"
```

---

## Additional Resources

- **Setup Guide**: `docs/development/setup_guide.md`
- **Architecture**: `docs/architecture/system_architecture.md`
- **WebSocket Docs**: See Channels documentation
- **Module Status**: `Documents/ExecutionPlan/MAP.md`

---

**Last Updated**: Module 9.6 (Backend V1 Finalization)
