# Authentication API Documentation

## Overview

DeltaCrown's authentication system uses JWT (JSON Web Tokens) for secure, stateless authentication. The API provides endpoints for user registration, login, token management, and profile operations.

## Base URL

```
Development: http://localhost:8000/api/auth/
Production: https://api.deltacrown.com/api/auth/
```

## Authentication

Most endpoints require authentication via JWT token in the Authorization header:

```
Authorization: Bearer <access_token>
```

## Token Lifecycle

- **Access Token**: Valid for 1 hour
- **Refresh Token**: Valid for 7 days
- Tokens are automatically rotated on refresh
- Old refresh tokens are blacklisted after rotation

---

## Endpoints

### 1. User Registration

**POST** `/api/auth/register/`

Register a new user account. User will be inactive until email verification.

#### Request Body

```json
{
  "username": "player1",
  "email": "player@example.com",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+8801234567890",
  "country": "Bangladesh",
  "role": "PLAYER"
}
```

#### Required Fields
- `username` (unique, alphanumeric + underscore)
- `email` (unique, valid email format)
- `password` (min 8 chars, must include letters and numbers)
- `password_confirm` (must match password)

#### Optional Fields
- `first_name`
- `last_name`
- `phone_number`
- `country`
- `role` (PLAYER, ORGANIZER - defaults to PLAYER)

#### Response (201 Created)

```json
{
  "message": "Registration successful. Please check your email to verify your account.",
  "user": {
    "id": 1,
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "username": "player1",
    "email": "player@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "role": "PLAYER",
    "phone_number": "+8801234567890",
    "country": "Bangladesh",
    "is_verified": false,
    "date_joined": "2025-11-04T10:00:00Z"
  }
}
```

#### Error Responses

**400 Bad Request** - Validation error
```json
{
  "username": ["A user with this username already exists."],
  "email": ["A user with this email already exists."],
  "password": ["This password is too common."]
}
```

---

### 2. User Login

**POST** `/api/auth/login/`

Authenticate user and receive JWT tokens. Supports login with email OR username.

#### Request Body

```json
{
  "email_or_username": "player1",
  "password": "SecurePass123!"
}
```

Or with email:

```json
{
  "email_or_username": "player@example.com",
  "password": "SecurePass123!"
}
```

#### Response (200 OK)

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "username": "player1",
    "email": "player@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "role": "PLAYER",
    "is_verified": true,
    "avatar": "/media/avatars/2025/11/04/player1.jpg",
    "bio": "Professional esports player",
    "date_joined": "2025-11-04T10:00:00Z",
    "last_login": "2025-11-04T12:00:00Z"
  }
}
```

#### Error Responses

**401 Unauthorized** - Invalid credentials
```json
{
  "detail": "Invalid credentials. Please check your email/username and password."
}
```

**401 Unauthorized** - Inactive account
```json
{
  "detail": "Account is inactive. Please verify your email or contact support."
}
```

---

### 3. Token Refresh

**POST** `/api/auth/token/refresh/`

Get a new access token using a valid refresh token.

#### Request Body

```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### Response (200 OK)

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### Error Responses

**401 Unauthorized** - Invalid or expired token
```json
{
  "detail": "Token is invalid or expired",
  "code": "token_not_valid"
}
```

---

### 4. Token Verify

**POST** `/api/auth/token/verify/`

Verify if a token is valid.

#### Request Body

```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### Response (200 OK)

```json
{}
```

#### Error Response (401 Unauthorized)

```json
{
  "detail": "Token is invalid or expired",
  "code": "token_not_valid"
}
```

---

### 5. User Logout

**POST** `/api/auth/logout/`

🔒 **Authentication Required**

Blacklist the refresh token to prevent reuse.

#### Request Headers

```
Authorization: Bearer <access_token>
```

#### Request Body

```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### Response (200 OK)

```json
{
  "message": "Logout successful"
}
```

---

### 6. Get User Profile

**GET** `/api/auth/me/`

🔒 **Authentication Required**

Get authenticated user's complete profile.

#### Request Headers

```
Authorization: Bearer <access_token>
```

#### Response (200 OK)

```json
{
  "id": 1,
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "username": "player1",
  "email": "player@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "role": "PLAYER",
  "phone_number": "+8801234567890",
  "date_of_birth": "1995-01-15",
  "age": 30,
  "country": "Bangladesh",
  "avatar": "/media/avatars/2025/11/04/player1.jpg",
  "bio": "Professional esports player with 5 years experience",
  "is_verified": true,
  "email_verified_at": "2025-11-04T10:30:00Z",
  "date_joined": "2025-11-04T10:00:00Z",
  "last_login": "2025-11-04T12:00:00Z"
}
```

---

### 7. Update User Profile

**PATCH** `/api/auth/me/`

🔒 **Authentication Required**

Update authenticated user's profile (partial update supported).

#### Request Headers

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

Or for avatar upload:

```
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

#### Request Body

```json
{
  "first_name": "John",
  "last_name": "Smith",
  "phone_number": "+8801234567890",
  "date_of_birth": "1995-01-15",
  "country": "Bangladesh",
  "bio": "Updated biography"
}
```

#### Response (200 OK)

Returns full user profile with updated data (same as GET `/api/auth/me/`)

#### Field Restrictions

**Cannot be changed:**
- `id`, `uuid`
- `username`
- `email`
- `role`
- `is_verified`
- Timestamps

**Can be updated:**
- `first_name`, `last_name`
- `phone_number`
- `date_of_birth`
- `country`
- `avatar`
- `bio` (max 500 characters)

---

### 8. Change Password

**POST** `/api/auth/change-password/`

🔒 **Authentication Required**

Change authenticated user's password.

#### Request Headers

```
Authorization: Bearer <access_token>
```

#### Request Body

```json
{
  "old_password": "SecurePass123!",
  "new_password": "NewSecurePass456!",
  "new_password_confirm": "NewSecurePass456!"
}
```

#### Response (200 OK)

```json
{
  "message": "Password changed successfully"
}
```

#### Error Responses

**400 Bad Request** - Invalid old password
```json
{
  "old_password": ["Old password is incorrect."]
}
```

**400 Bad Request** - Passwords don't match
```json
{
  "new_password_confirm": ["New passwords do not match."]
}
```

---

### 9. List Users

**GET** `/api/auth/users/`

🔒 **Authentication Required** (Admin/Organizer for all users)

List all users with pagination and filtering.

#### Request Headers

```
Authorization: Bearer <access_token>
```

#### Query Parameters

- `role` - Filter by role (PLAYER, ORGANIZER, ADMIN)
- `is_verified` - Filter by verification status (true/false)
- `search` - Search by username, email, or name
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20)

#### Example Requests

```
GET /api/auth/users/
GET /api/auth/users/?role=PLAYER
GET /api/auth/users/?is_verified=true
GET /api/auth/users/?search=john
GET /api/auth/users/?role=ORGANIZER&is_verified=true&page=2
```

#### Response (200 OK)

```json
{
  "count": 150,
  "next": "http://localhost:8000/api/auth/users/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "username": "player1",
      "email": "player@example.com",
      "full_name": "John Doe",
      "role": "PLAYER",
      "is_verified": true,
      "date_joined": "2025-11-04T10:00:00Z"
    },
    // ... more users
  ]
}
```

#### Access Control

- **Regular Users**: Can only see verified users
- **Organizers**: Can see all users
- **Admins**: Can see all users

---

## JWT Token Claims

Access tokens contain the following claims:

```json
{
  "token_type": "access",
  "exp": 1699101600,
  "iat": 1699098000,
  "jti": "unique-token-id",
  "user_id": 1,
  "username": "player1",
  "email": "player@example.com",
  "role": "PLAYER",
  "is_verified": true
}
```

---

## Error Codes

| Status Code | Description |
|------------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request - Validation error |
| 401 | Unauthorized - Invalid or missing token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found |
| 500 | Internal Server Error |

---

## Rate Limiting

| Endpoint | Limit |
|----------|-------|
| `/register/` | 5 requests per hour (anonymous) |
| `/login/` | 10 requests per minute (anonymous) |
| Other endpoints | 100 requests per hour (authenticated) |

---

## Code Examples

### Python (requests)

```python
import requests

# Register
response = requests.post('http://localhost:8000/api/auth/register/', json={
    'username': 'player1',
    'email': 'player@example.com',
    'password': 'SecurePass123!',
    'password_confirm': 'SecurePass123!',
})
print(response.json())

# Login
response = requests.post('http://localhost:8000/api/auth/login/', json={
    'email_or_username': 'player1',
    'password': 'SecurePass123!',
})
tokens = response.json()
access_token = tokens['access']

# Get profile
headers = {'Authorization': f'Bearer {access_token}'}
response = requests.get('http://localhost:8000/api/auth/me/', headers=headers)
print(response.json())

# Update profile
response = requests.patch('http://localhost:8000/api/auth/me/', 
    headers=headers,
    json={'bio': 'Updated bio'}
)
print(response.json())
```

### JavaScript (fetch)

```javascript
// Register
const registerResponse = await fetch('http://localhost:8000/api/auth/register/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'player1',
    email: 'player@example.com',
    password: 'SecurePass123!',
    password_confirm: 'SecurePass123!',
  }),
});
const registerData = await registerResponse.json();

// Login
const loginResponse = await fetch('http://localhost:8000/api/auth/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email_or_username: 'player1',
    password: 'SecurePass123!',
  }),
});
const { access, refresh } = await loginResponse.json();

// Get profile
const profileResponse = await fetch('http://localhost:8000/api/auth/me/', {
  headers: { 'Authorization': `Bearer ${access}` },
});
const profile = await profileResponse.json();
```

### cURL

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "player1",
    "email": "player@example.com",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!"
  }'

# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email_or_username": "player1",
    "password": "SecurePass123!"
  }'

# Get profile (replace TOKEN with actual access token)
curl -X GET http://localhost:8000/api/auth/me/ \
  -H "Authorization: Bearer TOKEN"

# Update profile
curl -X PATCH http://localhost:8000/api/auth/me/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"bio": "Updated bio"}'
```

---

## Best Practices

### 1. Token Storage

**Frontend (Browser)**
- Store access token in memory (React state, Vue data)
- Store refresh token in httpOnly cookie (secure)
- Never store tokens in localStorage (XSS vulnerability)

**Mobile Apps**
- Use secure storage (Keychain on iOS, KeyStore on Android)
- Encrypt tokens before storage

### 2. Token Refresh

Implement automatic token refresh:

```javascript
async function refreshAccessToken(refreshToken) {
  const response = await fetch('/api/auth/token/refresh/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh: refreshToken }),
  });
  const { access } = await response.json();
  return access;
}

// Use axios interceptor or similar to auto-refresh on 401
```

### 3. Logout Properly

Always blacklist refresh token on logout:

```javascript
async function logout(refreshToken) {
  await fetch('/api/auth/logout/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ refresh: refreshToken }),
  });
  // Clear tokens from storage
}
```

### 4. Handle Token Expiry

```javascript
function isTokenExpired(token) {
  const payload = JSON.parse(atob(token.split('.')[1]));
  return Date.now() >= payload.exp * 1000;
}
```

---

## Testing

### Manual Testing

Use the DRF browsable API at `http://localhost:8000/api/auth/` or tools like:
- Postman
- Insomnia
- cURL

### Automated Testing

```python
from rest_framework.test import APITestCase
from apps.accounts.models import User

class AuthAPITest(APITestCase):
    def test_register(self):
        response = self.client.post('/api/auth/register/', {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'password_confirm': 'TestPass123!',
        })
        self.assertEqual(response.status_code, 201)
    
    def test_login(self):
        User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        response = self.client.post('/api/auth/login/', {
            'email_or_username': 'testuser',
            'password': 'TestPass123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.json())
        self.assertIn('refresh', response.json())
```

---

**Last Updated**: November 4, 2025  
**API Version**: 1.0  
**Status**: ✅ Complete (BE-005)
