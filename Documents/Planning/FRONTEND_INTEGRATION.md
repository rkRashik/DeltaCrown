# Frontend Integration Guide

**Implements:**
- Documents/Planning/PART_2.3_REALTIME_SECURITY.md#websocket-frontend-integration
- Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md#frontend-api-integration

---

## Overview

This guide provides frontend developers with the information needed to integrate with DeltaCrown's REST API and WebSocket real-time features.

## Base URLs

```bash
# Development
API_BASE_URL=http://localhost:8000/api
WS_BASE_URL=ws://localhost:8000/ws

# Staging
API_BASE_URL=https://api-staging.deltacrown.com/api
WS_BASE_URL=wss://api-staging.deltacrown.com/ws

# Production
API_BASE_URL=https://api.deltacrown.com/api
WS_BASE_URL=wss://api.deltacrown.com/ws
```

---

## JWT Authentication Flow

### 1. Login (Obtain Tokens)

**Endpoint**: `POST /api/token/`

**Request**:
```json
{
  "username": "player1",
  "password": "SecurePassword123!"
}
```

**Response** (200 OK):
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Token Lifetimes**:
- `access`: 60 minutes (3600 seconds)
- `refresh`: 7 days (604800 seconds)

**Error Response** (401 Unauthorized):
```json
{
  "detail": "No active account found with the given credentials"
}
```

### 2. Refresh Access Token

**Endpoint**: `POST /api/token/refresh/`

**Request**:
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response** (200 OK):
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Notes**:
- Refresh tokens are rotated on use (old refresh token invalidated)
- Implement auto-refresh logic 5 minutes before expiry

### 3. Verify Token

**Endpoint**: `POST /api/token/verify/`

**Request**:
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response** (200 OK):
```json
{}
```

**Error Response** (401 Unauthorized):
```json
{
  "detail": "Token is invalid or expired",
  "code": "token_not_valid"
}
```

---

## WebSocket Real-Time Updates

### Connection Setup

```javascript
// Store tokens from login
const accessToken = 'eyJ0eXAiOiJKV1Q...';
const tournamentId = 123;

// Connect to tournament room
const ws = new WebSocket(
  `${WS_BASE_URL}/tournament/${tournamentId}/?token=${accessToken}`
);

// Handle connection open
ws.onopen = () => {
  console.log('Connected to tournament:', tournamentId);
};

// Handle incoming messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received event:', data.type, data);
  
  switch (data.type) {
    case 'match_started':
      handleMatchStarted(data);
      break;
    case 'score_updated':
      handleScoreUpdate(data);
      break;
    case 'match_completed':
      handleMatchCompleted(data);
      break;
    case 'bracket_updated':
      handleBracketUpdate(data);
      break;
    default:
      console.warn('Unknown event type:', data.type);
  }
};

// Handle errors
ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

// Handle connection close
ws.onclose = (event) => {
  if (event.code === 4002) {
    console.error('JWT expired - need to refresh and reconnect');
    // Trigger token refresh and reconnection
  } else if (event.code === 4003) {
    console.error('Invalid JWT - need to re-authenticate');
    // Redirect to login
  } else if (event.code === 4008) {
    console.error('Rate limited or policy violation');
  } else {
    console.log('Connection closed:', event.code, event.reason);
  }
};
```

### Event Types

#### match_started
Sent when a match transitions to LIVE status.

```json
{
  "type": "match_started",
  "match_id": 456,
  "tournament_id": 123,
  "round_number": 1,
  "participant1": "Team Alpha",
  "participant2": "Team Beta",
  "scheduled_time": "2025-11-10T15:00:00Z"
}
```

#### score_updated
Sent when a match score changes (before confirmation).

```json
{
  "type": "score_updated",
  "match_id": 456,
  "tournament_id": 123,
  "participant1_score": 2,
  "participant2_score": 1,
  "updated_by": "organizer_user"
}
```

#### match_completed
Sent when a match result is confirmed.

```json
{
  "type": "match_completed",
  "match_id": 456,
  "tournament_id": 123,
  "winner": "Team Alpha",
  "participant1_score": 3,
  "participant2_score": 1,
  "status": "COMPLETED"
}
```

#### bracket_updated
Sent when bracket progresses after a match.

```json
{
  "type": "bracket_updated",
  "bracket_id": 789,
  "tournament_id": 123,
  "updated_matches": [457, 458],
  "current_round": 2
}
```

### Handling Token Expiry

WebSocket connections require a valid JWT token. When the token expires (after 60 minutes), the connection will close with code `4002`.

**Recommended Pattern**:

```javascript
class TournamentWebSocket {
  constructor(tournamentId, getAccessToken) {
    this.tournamentId = tournamentId;
    this.getAccessToken = getAccessToken; // Function that returns valid token
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  connect() {
    const token = this.getAccessToken();
    this.ws = new WebSocket(
      `${WS_BASE_URL}/tournament/${this.tournamentId}/?token=${token}`
    );

    this.ws.onclose = (event) => {
      if (event.code === 4002 && this.reconnectAttempts < this.maxReconnectAttempts) {
        console.log('Token expired, refreshing and reconnecting...');
        this.reconnectAttempts++;
        
        // Refresh token, then reconnect
        refreshAccessToken().then(() => {
          setTimeout(() => this.connect(), 1000);
        });
      } else if (event.code === 4003) {
        console.error('Invalid token - redirecting to login');
        window.location.href = '/login';
      }
    };

    this.ws.onopen = () => {
      this.reconnectAttempts = 0; // Reset on successful connection
    };
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// Usage
const wsClient = new TournamentWebSocket(123, () => getStoredAccessToken());
wsClient.connect();
```

---

## Rate Limits

### WebSocket Connections
- **Per User**: 3 concurrent connections
- **Per IP**: 10 concurrent connections
- **Per Tournament Room**: 2000 members max

### WebSocket Messages
- **Rate**: 10 messages/second per user
- **Burst**: 20 messages (burst capacity)
- **Payload Size**: 16 KB max

### Error Codes
- `4008`: Policy Violation (rate limited, oversized payload)
- `4009`: Message Too Big

**Client Recommendations**:
- Implement exponential backoff on reconnection
- Buffer outgoing messages to respect rate limits
- Monitor connection close codes for policy violations

---

## CORS Configuration

For local development, ensure your frontend origin is whitelisted:

**Backend `.env`**:
```bash
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://localhost:5173
WS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

**Frontend Config** (Vite example):
```javascript
// vite.config.js
export default {
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
};
```

---

## Example React Hook

```typescript
import { useEffect, useRef, useState } from 'react';

interface TournamentEvent {
  type: string;
  [key: string]: any;
}

export function useTournamentWebSocket(
  tournamentId: number,
  accessToken: string
) {
  const ws = useRef<WebSocket | null>(null);
  const [events, setEvents] = useState<TournamentEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!accessToken || !tournamentId) return;

    const url = `ws://localhost:8000/ws/tournament/${tournamentId}/?token=${accessToken}`;
    ws.current = new WebSocket(url);

    ws.current.onopen = () => {
      console.log('Connected to tournament', tournamentId);
      setIsConnected(true);
    };

    ws.current.onmessage = (event) => {
      const data: TournamentEvent = JSON.parse(event.data);
      setEvents((prev) => [...prev, data]);
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.current.onclose = (event) => {
      console.log('Disconnected:', event.code, event.reason);
      setIsConnected(false);
      
      if (event.code === 4002) {
        // Handle token expiry
        console.error('Token expired - refresh needed');
      }
    };

    return () => {
      ws.current?.close();
    };
  }, [tournamentId, accessToken]);

  return { events, isConnected };
}
```

---

## Testing

### WebSocket Connection Test

```bash
# Install wscat
npm install -g wscat

# Connect to tournament
wscat -c "ws://localhost:8000/ws/tournament/123/?token=YOUR_JWT_TOKEN"

# You should see connection success and any live events
```

### API Health Check

```bash
# Basic health
curl http://localhost:8000/healthz

# Readiness (with DB + Redis checks)
curl http://localhost:8000/readiness
```

---

## Troubleshooting

### WebSocket won't connect
- Check JWT token is valid (`POST /api/token/verify/`)
- Verify tournament ID exists
- Check browser console for CORS errors
- Ensure WebSocket URL uses correct protocol (`ws://` for local, `wss://` for production)

### Connection closes immediately
- Code 4002: Token expired - refresh and reconnect
- Code 4003: Invalid token - re-authenticate
- Code 4008: Rate limited - reduce message frequency

### No events received
- Verify you're subscribed to correct tournament
- Check server logs for broadcast errors
- Ensure match/bracket events are being triggered (check admin or create test data)

---

## Support

For integration issues or questions:
- Backend API Issues: Check server logs or `/readiness` endpoint
- WebSocket Issues: Check browser developer tools → Network → WS tab
- Documentation: See `Documents/Planning/PART_2.3_REALTIME_SECURITY.md`
