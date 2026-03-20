# 08 — Authentication & Security

## Overview

The application uses a **JWT Bearer token** authentication system with **bcrypt** password hashing.

- **Library**: `python-jose[cryptography]` for JWT encoding/decoding
- **Hashing**: `bcrypt` with automatic salt generation
- **Token type**: Bearer (sent in `Authorization` header)
- **Token lifetime**: 8 hours (configurable)

---

## Authentication Flow

### Registration

```
Client                          Backend                         Database
  │                               │                               │
  ├─ POST /api/auth/register ────▶│                               │
  │  {nickname, password}          │                               │
  │                               ├─ Check nickname uniqueness ──▶│
  │                               │◀── Result ───────────────────│
  │                               │                               │
  │                               ├─ bcrypt.hash(password)        │
  │                               │                               │
  │                               ├─ INSERT user ────────────────▶│
  │                               │◀── User record ──────────────│
  │                               │                               │
  │                               ├─ Create JWT {sub: user_id,    │
  │                               │              exp: now+8h}     │
  │                               │                               │
  │◀── {access_token, user} ─────│                               │
```

### Login

```
Client                          Backend                         Database
  │                               │                               │
  ├─ POST /api/auth/login ───────▶│                               │
  │  {nickname, password}          │                               │
  │                               ├─ SELECT user by nickname ────▶│
  │                               │◀── User record ──────────────│
  │                               │                               │
  │                               ├─ bcrypt.verify(password,      │
  │                               │               hash) → bool   │
  │                               │                               │
  │                               ├─ Create JWT if verified       │
  │                               │                               │
  │◀── {access_token, user} ─────│                               │
  │  or 401 Unauthorized          │                               │
```

### Authenticated Request

```
Client                          Backend                         Database
  │                               │                               │
  ├─ GET /api/uploads/ ──────────▶│                               │
  │  Authorization: Bearer <jwt>   │                               │
  │                               ├─ Decode JWT                   │
  │                               ├─ Extract user_id from 'sub'   │
  │                               ├─ SELECT user by id ──────────▶│
  │                               │◀── User record ──────────────│
  │                               │                               │
  │                               ├─ Execute route handler        │
  │                               │  (user injected as dep)       │
  │                               │                               │
  │◀── Response ─────────────────│                               │
```

---

## JWT Token Structure

### Payload

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "exp": 1742500000
}
```

| Claim | Type | Description |
|-------|------|-------------|
| `sub` | string (UUID) | User ID |
| `exp` | int (timestamp) | Expiration time |

### Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `JWT_SECRET` | `change-me-in-production` | **Must be changed in production** |
| `JWT_ALGORITHM` | `HS256` | HMAC-SHA256 signing |
| `JWT_EXPIRE_MINUTES` | `480` | 8-hour token lifetime |

> **Security Warning**: The default `JWT_SECRET` is insecure. Always set a strong random secret in production via the `JWT_SECRET` environment variable.

---

## Password Hashing

Passwords are hashed using `bcrypt` with automatic salt generation:

```python
# Hashing (registration)
password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

# Verification (login)
is_valid = bcrypt.checkpw(password.encode(), stored_hash.encode())
```

- **Algorithm**: bcrypt (Blowfish-derived)
- **Salt**: Automatically generated per hash (stored within the hash string)
- **Rounds**: Default bcrypt work factor (12 rounds)
- **Output**: 60-character hash string stored in `users.password_hash`

---

## Frontend Token Management

### Storage

Tokens are stored in `localStorage`:

```typescript
// After login/register
localStorage.setItem('rsv_token', accessToken)
localStorage.setItem('rsv_nickname', user.nickname)

// On logout
localStorage.removeItem('rsv_token')
localStorage.removeItem('rsv_nickname')
```

### Token Injection

Every API request automatically includes the token:

```typescript
function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('rsv_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}
```

### Token Validation on Load

When the app loads, `AuthContext` validates the stored token:

```typescript
useEffect(() => {
  const token = localStorage.getItem('rsv_token')
  if (token) {
    getMe()
      .then(user => setAuth(token, user))
      .catch(() => logout())  // Token expired or invalid
  } else {
    setLoading(false)
  }
}, [])
```

### SSE Token Handling

Since `EventSource` doesn't support custom headers, SSE endpoints receive the token as a query parameter:

```typescript
const source = new EventSource(
  `/api/validations/batch/${batchId}/progress?token=${token}`
)
```

---

## Endpoint Protection

### Public Endpoints (No Auth Required)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Health check |
| `POST` | `/api/auth/register` | User registration |
| `POST` | `/api/auth/login` | User login |
| `POST` | `/api/chat/stream` | AI chat (public by design) |
| `POST` | `/api/chat/upload` | Chat file upload |

### Protected Endpoints (Bearer JWT Required)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/auth/me` | Current user profile |
| `POST` | `/api/uploads/` | Upload file |
| `GET` | `/api/uploads/` | List uploads |
| `GET` | `/api/uploads/{id}` | Get upload detail |
| `GET` | `/api/uploads/{id}/content` | Preview file content |
| `POST` | `/api/validations/{id}/run` | Run validation |
| `GET` | `/api/validations/{id}` | Get results |
| `GET` | `/api/validations/{id}/issues` | Get issues |
| `GET` | `/api/validations/{id}/pdf` | Download PDF report |
| `GET` | `/api/validations/{id}/annotated-pdf` | Download annotated PDF |
| `POST` | `/api/validations/batch` | Batch validation |

---

## Route Guard (Frontend)

The `ProtectedRoute` component wraps all authenticated routes:

```typescript
function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()

  if (loading) return <Spinner />
  if (!user) return <Navigate to="/login" replace />
  return children
}
```

---

## Security Considerations

| Aspect | Status | Notes |
|--------|--------|-------|
| Password hashing | ✅ bcrypt | Industry standard, salted |
| JWT signing | ✅ HS256 | Symmetric key (adequate for single-service) |
| Token expiry | ✅ 8 hours | Configurable |
| HTTPS | ⚠️ Not enforced | Recommended for production (terminate at reverse proxy) |
| Refresh tokens | ❌ Not implemented | User must re-login after 8 hours |
| Rate limiting | ❌ Not implemented | Consider for production |
| CORS | ✅ Configured | Restricted to configured origins |
| Token storage | ⚠️ localStorage | Vulnerable to XSS; consider HttpOnly cookies for production |
| Chat endpoints | ⚠️ Public | No auth on chat — by design for accessibility |
| JWT secret | ⚠️ Default insecure | **Must be overridden in production** |
