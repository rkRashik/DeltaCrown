# Security Best Practices

## Table of Contents

1. [Introduction](#introduction)
2. [Authentication & Authorization](#authentication--authorization)
3. [API Security](#api-security)
4. [Handling Sensitive Data](#handling-sensitive-data)
5. [XSS, CSRF, and Clickjacking Prevention](#xss-csrf-and-clickjacking-prevention)
6. [Secure Component Patterns](#secure-component-patterns)
7. [Deployment Security Checklist](#deployment-security-checklist)

---

## Introduction

This guide outlines **security best practices** for frontend developers working on the DeltaCrown Organizer Console. While the backend implements most security controls, the frontend plays a critical role in:

- Protecting user credentials and tokens
- Preventing client-side vulnerabilities (XSS, CSRF)
- Avoiding accidental data leaks
- Providing secure user experiences

**Audience**: Frontend developers (not security specialists)

**Scope**: Client-side security only (see backend security docs for server-side practices)

---

## Authentication & Authorization

### 1. Token Storage

**Best Practice**: Store JWT tokens securely to prevent unauthorized access.

**✅ Recommended Approaches:**

**Option A: HttpOnly Cookies (Preferred)**

Tokens stored in HttpOnly cookies cannot be accessed by JavaScript, preventing XSS theft.

```typescript
// Backend sets cookie (example for reference)
res.cookie('access_token', token, {
  httpOnly: true,
  secure: true, // HTTPS only
  sameSite: 'strict',
  maxAge: 3600000, // 1 hour
});

// Frontend: No manual token handling needed
// SDK automatically includes cookies in requests
```

**Option B: Memory-Only Storage (Session-based)**

Store tokens in React state/context, cleared on page refresh.

```typescript
// AuthProvider (Client Component)
'use client';

export function AuthProvider({ children }) {
  const [token, setToken] = useState<string | null>(null);

  return (
    <AuthContext.Provider value={{ token, setToken }}>
      {children}
    </AuthContext.Provider>
  );
}

// Token lost on refresh → user re-authenticates
```

**❌ Avoid: localStorage for sensitive tokens**

Tokens in `localStorage` are vulnerable to XSS attacks.

```typescript
// ❌ BAD: Vulnerable to XSS
localStorage.setItem('access_token', token);

// If an attacker injects script:
const token = localStorage.getItem('access_token');
// → Token stolen, account compromised
```

**Use localStorage only for:**

- Non-sensitive preferences (theme, language)
- Public data (cached tournament lists)

---

### 2. Token Expiration Handling

**Best Practice**: Handle token expiration gracefully to prevent stale sessions.

**✅ Recommended Pattern:**

```typescript
// SDK interceptor
client.setRequestInterceptor(async (config) => {
  const token = await getToken();
  
  // Check expiration
  if (isTokenExpired(token)) {
    const newToken = await refreshToken();
    setToken(newToken);
    config.headers.Authorization = `Bearer ${newToken}`;
  } else {
    config.headers.Authorization = `Bearer ${token}`;
  }
  
  return config;
});

function isTokenExpired(token: string): boolean {
  const payload = JSON.parse(atob(token.split('.')[1]));
  return Date.now() / 1000 > payload.exp;
}
```

---

### 3. Role-Based UI Rendering

**Best Practice**: Render UI elements based on user roles, but **ALWAYS validate on the backend**.

**✅ Correct Approach:**

```typescript
// Frontend: Hide UI for unauthorized users
const { user } = useAuth();

if (!user?.roles.includes('organizer')) {
  return <div>Access denied. Organizer role required.</div>;
}

// Backend MUST also validate:
// @require_role('organizer')
// def create_tournament(request):
//     ...
```

**❌ Security Anti-Pattern:**

```typescript
// ❌ BAD: Hiding UI doesn't prevent API access
{user?.roles.includes('organizer') && (
  <button onClick={() => client.tournaments.create(data)}>
    Create Tournament
  </button>
)}

// Attacker can still call client.tournaments.create() via console!
// Backend MUST validate roles.
```

**Key Principle**: Frontend checks are **UX only**, not security.

---

### 4. Avoid Exposing Organizer Tools to Non-Organizers

**Best Practice**: Use route guards and conditional rendering to prevent accidental access.

**✅ Route Guard Example:**

```typescript
// app/organizer/layout.tsx (Server Component)
import { redirect } from 'next/navigation';
import { getCurrentUser } from '@/lib/auth';

export default async function OrganizerLayout({ children }) {
  const user = await getCurrentUser();
  
  if (!user || !user.roles.includes('organizer')) {
    redirect('/login?error=unauthorized');
  }
  
  return <>{children}</>;
}
```

---

## API Security

### 5. Never Trust Frontend Inputs

**Best Practice**: Client-side validation is for **UX only**. Backend must validate all inputs.

**✅ Correct Layered Validation:**

```typescript
// Frontend: Immediate user feedback
function CreateTournamentForm() {
  const [name, setName] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    // Client-side validation (UX)
    if (!name || name.length < 3) {
      setError('Name must be at least 3 characters');
      return;
    }

    try {
      // Backend validates again (SECURITY)
      await client.tournaments.create({ name, ... });
    } catch (err) {
      setError(err.message);
    }
  };

  return (/* form UI */);
}
```

**Backend MUST validate**:

- Input length, format, type
- Business rules (e.g., max participants ≤ 128)
- Authorization (user has permission)

---

### 6. HTTPS-Only Communication

**Best Practice**: Always use HTTPS for API communication. Never send tokens over HTTP.

**✅ Environment Configuration:**

```bash
# .env.local
NEXT_PUBLIC_API_BASE_URL=https://api.deltacrown.example.com

# ❌ NEVER use HTTP in production
# NEXT_PUBLIC_API_BASE_URL=http://api.deltacrown.example.com
```

**Verification:**

```typescript
// SDK initialization
const client = new DeltaCrownClient({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL,
});

// Check in dev console:
console.assert(
  client.baseURL.startsWith('https://'),
  'API must use HTTPS'
);
```

---

### 7. Avoid Leaking IDs in Logs

**Best Practice**: Don't log sensitive identifiers (user IDs, tournament IDs, tokens).

**❌ Bad Logging:**

```typescript
// ❌ BAD: Logs user ID, visible in browser console
console.log('User logged in:', user.id, user.email);

// ❌ BAD: Token in logs
console.log('Token:', token);
```

**✅ Safe Logging:**

```typescript
// ✅ GOOD: Generic message
console.log('User logged in successfully');

// ✅ GOOD: Sanitized logs (dev only)
if (process.env.NODE_ENV === 'development') {
  console.debug('User ID:', user.id);
}
```

**Production Logging**: Use a proper logging service (Sentry, LogRocket) with PII redaction.

---

### 8. Rate Limit Awareness

**Best Practice**: Respect rate limits to avoid lockouts and degraded performance.

**API Rate Limits** (see [API_REFERENCE.md](./API_REFERENCE.md#rate-limiting)):

- Authenticated: 1000 req/hour
- Unauthenticated: 100 req/hour

**✅ Frontend Strategies:**

1. **Cache responses** (React Query):

```typescript
const { data } = useQuery({
  queryKey: ['tournaments'],
  queryFn: () => client.tournaments.list(),
  staleTime: 5 * 60 * 1000, // Cache 5 minutes
});
```

2. **Debounce search inputs**:

```typescript
const debouncedSearch = useMemo(
  () => debounce((query) => client.search(query), 300),
  []
);
```

3. **Use pagination** instead of fetching all data.

---

## Handling Sensitive Data

### 9. Mask Personal Information in UI

**Best Practice**: Redact or mask sensitive data (emails, payment info) unless necessary.

**✅ Example:**

```typescript
// Mask email
function maskEmail(email: string): string {
  const [local, domain] = email.split('@');
  return `${local[0]}***@${domain}`;
}

// Usage
<div>Email: {maskEmail(user.email)}</div>
// Output: "j***@example.com"
```

---

### 10. Avoid Logging Raw API Responses

**Best Practice**: Don't log full API responses (may contain sensitive data).

**❌ Bad:**

```typescript
// ❌ BAD: Full response logged
const user = await client.auth.getCurrentUser();
console.log('User response:', user); // May include PII
```

**✅ Good:**

```typescript
// ✅ GOOD: Log only what's needed
const user = await client.auth.getCurrentUser();
console.log('User loaded:', user.username);
```

---

### 11. Avoid Sending Unnecessary Data to Components

**Best Practice**: Pass only required props to components. Don't leak extra data.

**❌ Bad:**

```typescript
// ❌ BAD: Entire user object passed (includes sensitive fields)
<UserCard user={user} />

// UserCard only needs username and avatar
```

**✅ Good:**

```typescript
// ✅ GOOD: Only necessary props
<UserCard username={user.username} avatar={user.avatar_url} />
```

---

## XSS, CSRF, and Clickjacking Prevention

### 12. React's Built-In XSS Protection

**What React Protects Against:**

React escapes user input by default, preventing most XSS attacks.

**✅ Safe (Auto-Escaped):**

```tsx
const userInput = '<script>alert("XSS")</script>';

// React escapes this automatically
<div>{userInput}</div>
// Renders as text: "&lt;script&gt;alert("XSS")&lt;/script&gt;"
```

**❌ Dangerous Override:**

```tsx
// ❌ BAD: Bypasses React's escaping
<div dangerouslySetInnerHTML={{ __html: userInput }} />
// Executes script! XSS vulnerability.
```

**Only use `dangerouslySetInnerHTML` for:**

- Trusted, sanitized HTML (e.g., from a CMS)
- Always sanitize with a library like **DOMPurify**:

```typescript
import DOMPurify from 'dompurify';

const sanitized = DOMPurify.sanitize(userInput);
<div dangerouslySetInnerHTML={{ __html: sanitized }} />
```

---

### 13. CSRF Protection with SameSite Cookies

**What is CSRF?** Cross-Site Request Forgery: an attacker tricks a user's browser into making unwanted requests.

**Protection**: Use `SameSite` cookies to prevent cross-origin requests.

**Backend Cookie Configuration** (example for reference):

```python
# Backend sets cookies with SameSite
res.cookie('access_token', token, {
  httpOnly: True,
  secure: True,
  sameSite: 'Strict', # or 'Lax'
})
```

**Frontend**: No action needed if backend sets `SameSite` correctly.

---

### 14. Prevent Clickjacking with X-Frame-Options

**What is Clickjacking?** Embedding your site in an iframe to trick users into clicking malicious links.

**Protection**: Backend sets `X-Frame-Options` header.

**Backend Configuration** (example):

```python
# Django middleware
MIDDLEWARE = [
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

X_FRAME_OPTIONS = 'DENY'  # or 'SAMEORIGIN'
```

**Frontend**: No action needed. Header is set by backend.

---

### 15. Content Security Policy (CSP)

**What is CSP?** HTTP header that restricts sources of scripts, styles, images, etc.

**Backend Configuration** (example):

```python
# Django CSP middleware
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")  # Avoid 'unsafe-inline' if possible
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
```

**Frontend Impact**: Inline scripts/styles may be blocked. Use external files.

**❌ Blocked by CSP:**

```html
<script>alert('inline')</script>
```

**✅ Allowed:**

```html
<script src="/app.js"></script>
```

---

## Secure Component Patterns

### 16. Input Sanitization

**Best Practice**: Sanitize user input before displaying or sending to API.

**✅ Sanitize HTML:**

```typescript
import DOMPurify from 'dompurify';

function CommentDisplay({ comment }: { comment: string }) {
  const sanitized = DOMPurify.sanitize(comment);
  return <div dangerouslySetInnerHTML={{ __html: sanitized }} />;
}
```

**✅ Sanitize URLs:**

```typescript
// Prevent javascript: URLs
function SafeLink({ href, children }: { href: string; children: React.ReactNode }) {
  const isSafe = href.startsWith('http://') || href.startsWith('https://');
  
  if (!isSafe) {
    console.warn('Unsafe URL blocked:', href);
    return <span>{children}</span>;
  }
  
  return <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
}
```

---

### 17. Safe File Upload Handling

**Best Practice**: Validate file types, sizes, and names on frontend (UX) and backend (security).

**✅ Frontend Validation:**

```typescript
function FileUpload() {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate type
    const allowedTypes = ['image/png', 'image/jpeg', 'application/pdf'];
    if (!allowedTypes.includes(file.type)) {
      alert('Invalid file type. Only PNG, JPEG, PDF allowed.');
      return;
    }

    // Validate size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      alert('File too large. Max 5MB.');
      return;
    }

    // Upload to backend (which validates again)
    uploadFile(file);
  };

  return <input type="file" onChange={handleChange} accept=".png,.jpg,.pdf" />;
}
```

**Backend MUST validate**:

- File type (check magic bytes, not just extension)
- File size
- Scan for malware (if applicable)

---

### 18. Avoid Generating Insecure URLs

**Best Practice**: Don't construct URLs from untrusted input.

**❌ Bad:**

```typescript
// ❌ BAD: User input in URL
const redirect = new URLSearchParams(window.location.search).get('redirect');
window.location.href = redirect; // Could be http://evil.com
```

**✅ Good:**

```typescript
// ✅ GOOD: Whitelist allowed redirects
const redirect = new URLSearchParams(window.location.search).get('redirect');
const allowedRedirects = ['/dashboard', '/tournaments', '/profile'];

if (redirect && allowedRedirects.includes(redirect)) {
  window.location.href = redirect;
} else {
  window.location.href = '/dashboard'; // Default safe redirect
}
```

---

### 19. Secure API Error Handling

**Best Practice**: Don't expose sensitive error details to users.

**❌ Bad:**

```typescript
// ❌ BAD: Exposes backend error
try {
  await client.tournaments.create(data);
} catch (err) {
  alert(err.response.data); // May include SQL errors, stack traces
}
```

**✅ Good:**

```typescript
// ✅ GOOD: Generic user-facing message
try {
  await client.tournaments.create(data);
} catch (err) {
  if (err instanceof ApiError) {
    // Show user-friendly message
    toast.error('Failed to create tournament. Please try again.');
    
    // Log full error for debugging (dev only)
    if (process.env.NODE_ENV === 'development') {
      console.error('API Error:', err);
    }
  }
}
```

---

### 20. Prevent Open Redirects

**Best Practice**: Validate redirect URLs to prevent phishing attacks.

**✅ Safe Redirect:**

```typescript
function LoginPage() {
  const router = useRouter();
  const { redirect } = router.query;

  const handleLogin = async (credentials) => {
    await client.auth.login(credentials);
    
    // Validate redirect is internal
    if (redirect && redirect.startsWith('/')) {
      router.push(redirect);
    } else {
      router.push('/dashboard');
    }
  };

  return (/* login form */);
}
```

---

## Deployment Security Checklist

### 21. Environment File Safety

**Best Practice**: Never commit `.env.local` or expose secrets in client-side code.

**✅ Checklist:**

- ✅ `.env.local` is in `.gitignore`
- ✅ Secrets (API keys, DB URLs) are **NOT** prefixed with `NEXT_PUBLIC_`
- ✅ Production secrets stored in secure vault (GitHub Secrets, AWS Secrets Manager)

**❌ Bad:**

```bash
# ❌ BAD: Secret exposed to browser
NEXT_PUBLIC_SECRET_API_KEY=abc123
```

**✅ Good:**

```bash
# ✅ GOOD: Only base URL is public
NEXT_PUBLIC_API_BASE_URL=https://api.deltacrown.example.com

# Server-side only (no NEXT_PUBLIC_ prefix)
DATABASE_URL=postgresql://user:pass@localhost/db
```

---

### 22. Disable Debug Mode in Production

**Best Practice**: Ensure debug tools are disabled in production builds.

**✅ Production Build:**

```typescript
// next.config.js
module.exports = {
  reactStrictMode: true,
  productionBrowserSourceMaps: false, // Disable source maps
};
```

**Verify:**

```bash
NODE_ENV=production pnpm build
```

**Never deploy** with `NODE_ENV=development`.

---

### 23. Build Asset Integrity

**Best Practice**: Use Subresource Integrity (SRI) for third-party scripts.

**✅ Example:**

```html
<!-- External script with SRI -->
<script
  src="https://cdn.example.com/library.js"
  integrity="sha384-oqVuAfXRKap7fdgcCY5uykM6+R9GqQ8K/ux..."
  crossorigin="anonymous"
></script>
```

**Next.js handles this automatically** for bundled assets.

---

### 24. Security Headers

**Best Practice**: Ensure backend sets security headers.

**Required Headers** (backend responsibility, listed for awareness):

| Header                     | Purpose                              | Example Value                          |
| -------------------------- | ------------------------------------ | -------------------------------------- |
| `X-Content-Type-Options`   | Prevent MIME sniffing                | `nosniff`                              |
| `X-Frame-Options`          | Prevent clickjacking                 | `DENY` or `SAMEORIGIN`                 |
| `Strict-Transport-Security`| Force HTTPS                          | `max-age=31536000; includeSubDomains`  |
| `Content-Security-Policy`  | Restrict resource sources            | `default-src 'self'`                   |
| `Referrer-Policy`          | Control referrer information         | `no-referrer-when-downgrade`           |

**Frontend**: No action needed. Verify headers in browser DevTools (Network tab).

---

### 25. Monitor for Vulnerabilities

**Best Practice**: Regularly scan dependencies for known vulnerabilities.

**✅ Run Security Audit:**

```powershell
pnpm audit
pnpm audit --fix  # Auto-fix fixable issues
```

**Review Output:**

```
found 3 vulnerabilities (1 moderate, 2 high)
run `pnpm audit fix` to fix them, or `pnpm audit` for details
```

**Update Dependencies:**

```powershell
pnpm update
```

**Use Dependabot** (GitHub) to automate dependency updates.

---

## Summary: Top 10 Security Rules for Frontend Devs

1. **Never store tokens in localStorage** (use HttpOnly cookies or memory)
2. **Always validate on backend** (frontend validation is UX only)
3. **Use HTTPS-only** in production
4. **Avoid `dangerouslySetInnerHTML`** unless sanitized with DOMPurify
5. **Don't log sensitive data** (tokens, user IDs, PII)
6. **Validate file uploads** (type, size, name)
7. **Whitelist redirects** (prevent open redirect attacks)
8. **Set `SameSite` cookies** (prevent CSRF)
9. **Never commit `.env.local`** or expose secrets
10. **Run `pnpm audit`** regularly to catch vulnerabilities

---

## Additional Resources

- **OWASP Top 10**: [https://owasp.org/www-project-top-ten/](https://owasp.org/www-project-top-ten/)
- **Next.js Security**: [https://nextjs.org/docs/advanced-features/security-headers](https://nextjs.org/docs/advanced-features/security-headers)
- **React Security**: [https://reactjs.org/docs/dom-elements.html#dangerouslysetinnerhtml](https://reactjs.org/docs/dom-elements.html#dangerouslysetinnerhtml)
- **DOMPurify**: [https://github.com/cure53/DOMPurify](https://github.com/cure53/DOMPurify)

For deployment security, see backend security documentation.

---

**Stay secure! 🔒**
