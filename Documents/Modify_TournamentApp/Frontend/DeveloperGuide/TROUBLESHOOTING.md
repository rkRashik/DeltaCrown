# Troubleshooting Guide

## Table of Contents

1. [Introduction](#introduction)
2. [TypeScript & SDK Type Errors](#typescript--sdk-type-errors)
3. [API Request Failures](#api-request-failures)
4. [Tailwind & Styling Issues](#tailwind--styling-issues)
5. [Design Tokens Not Loading](#design-tokens-not-loading)
6. [Backend Connection Issues](#backend-connection-issues)
7. [Dependency & Version Mismatches](#dependency--version-mismatches)
8. [Build & Compilation Errors](#build--compilation-errors)
9. [Runtime Errors](#runtime-errors)
10. [Performance Issues](#performance-issues)
11. [When to Ask for Help](#when-to-ask-for-help)

---

## Introduction

This guide covers **common issues** encountered during DeltaCrown Organizer Console development and their solutions. Each section follows an **FAQ style**:

- **Symptom**: What you're seeing
- **Likely Cause**: Why it's happening
- **How to Fix**: Step-by-step solution

If you don't find your issue here, see [When to Ask for Help](#when-to-ask-for-help).

---

## TypeScript & SDK Type Errors

### Error: `Property 'X' does not exist on type 'Y'`

**Symptom:**

```
Type error: Property 'prize_pool' does not exist on type 'Tournament'.
```

**Likely Cause:**

- SDK types are outdated (you're using an old version)
- You're accessing a field that doesn't exist in the DTO
- TypeScript strictness is catching a typo

**How to Fix:**

1. **Check the SDK version**:

```powershell
pnpm list deltacrown-sdk
```

Ensure it matches the backend version (check with backend team).

2. **Re-link the SDK** (if using local link):

```powershell
cd ../../../frontend_sdk
pnpm link --global
cd ../Documents/Modify_TournamentApp/Frontend
pnpm link --global deltacrown-sdk
```

3. **Check the DTO definition** in `frontend_sdk/src/types/`:

```typescript
// frontend_sdk/src/types/tournament.ts
export interface Tournament {
  id: number;
  name: string;
  prize_pool?: string; // ← Check if this field exists
  // ...
}
```

4. **Rebuild the SDK** (if you made changes):

```powershell
cd ../../../frontend_sdk
pnpm build
```

5. **Restart the dev server**:

```powershell
# In frontend directory
pnpm dev
```

---

### Error: `Cannot find module 'deltacrown-sdk'`

**Symptom:**

```
Module not found: Can't resolve 'deltacrown-sdk'
```

**Likely Cause:**

- SDK is not installed or linked
- SDK symlink is broken

**How to Fix:**

1. **Re-link the SDK**:

```powershell
cd ../../../frontend_sdk
pnpm link --global
cd ../Documents/Modify_TournamentApp/Frontend
pnpm link --global deltacrown-sdk
```

2. **Verify the link**:

```powershell
ls node_modules/deltacrown-sdk
```

You should see SDK files.

3. **Alternative: Install from npm** (if published):

```powershell
pnpm add deltacrown-sdk
```

4. **Restart the dev server**.

---

### Error: `Type 'X' is not assignable to type 'Y'`

**Symptom:**

```
Type 'string' is not assignable to type 'number'.
```

**Likely Cause:**

- Type mismatch between what the API returns and what your code expects
- SDK types don't match backend schema

**How to Fix:**

1. **Check the OpenAPI schema** at `/api/schema/`:

```powershell
curl https://api-staging.deltacrown.example.com/api/schema/ | Select-String "prize_pool"
```

2. **Update SDK types** to match schema (if incorrect):

```typescript
// frontend_sdk/src/types/tournament.ts
prize_pool: string; // Backend returns string, not number
```

3. **Cast the type** (temporary workaround):

```typescript
const prizePool = Number(tournament.prize_pool);
```

4. **Report the discrepancy** to the backend team if schema is wrong.

---

## API Request Failures

### Error: `Failed to fetch` or `Network Error`

**Symptom:**

Browser console shows:

```
Failed to fetch
NetworkError when attempting to fetch resource.
```

**Likely Cause:**

- Backend is not running or unreachable
- Incorrect `NEXT_PUBLIC_API_BASE_URL`
- CORS issue

**How to Fix:**

1. **Check environment variable**:

```powershell
# In .env.local
NEXT_PUBLIC_API_BASE_URL=https://api-staging.deltacrown.example.com
```

2. **Test the API manually**:

```powershell
curl https://api-staging.deltacrown.example.com/api/schema/
```

If this fails, the backend is down or the URL is wrong.

3. **Check for CORS errors** in browser console:

```
Access to fetch at 'https://api-staging...' from origin 'http://localhost:3000' has been blocked by CORS policy.
```

**Fix**: Backend must allow `http://localhost:3000` in CORS settings. Contact backend team.

4. **Verify local backend** (if running locally):

```powershell
# Check if backend is running
curl http://localhost:8000/api/schema/
```

If this fails, start the backend:

```powershell
cd G:\My Projects\WORK\DeltaCrown
python manage.py runserver
```

---

### Error: `401 Unauthorized`

**Symptom:**

API requests return `401`:

```json
{ "detail": "Authentication credentials were not provided." }
```

**Likely Cause:**

- No auth token provided
- Token expired
- Token invalid

**How to Fix:**

1. **Check if user is logged in**:

```typescript
// In any component
const { user } = useAuth();
console.log('User:', user);
```

If `user` is `null`, the user is not authenticated.

2. **Login flow**: Redirect to login page:

```typescript
if (!user) {
  router.push('/login');
}
```

3. **Check token in SDK client**:

```typescript
const client = new DeltaCrownClient({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL,
  getToken: () => localStorage.getItem('access_token'),
});
```

4. **Manually test with token**:

```powershell
$token = "your_token_here"
curl -H "Authorization: Bearer $token" https://api-staging.deltacrown.example.com/api/tournaments/v1/organizer/tournaments/
```

If this returns `401`, the token is invalid. Re-login to get a new token.

---

### Error: `403 Forbidden`

**Symptom:**

```json
{ "detail": "You do not have permission to perform this action." }
```

**Likely Cause:**

- User lacks required role (e.g., trying to access organizer endpoint as a player)
- Insufficient permissions

**How to Fix:**

1. **Check user role**:

```typescript
const { user } = useAuth();
console.log('Roles:', user?.roles);
```

2. **Verify endpoint requirements** in [API_REFERENCE.md](./API_REFERENCE.md):

```
GET /api/tournaments/v1/organizer/tournaments/
Auth: 👔 Organizer
```

If user is not an organizer, they can't access this endpoint.

3. **Use the correct endpoint** for the user's role:

```typescript
// ❌ Wrong: Organizer endpoint for a player
await client.tournaments.list(); // Requires organizer role

// ✅ Correct: Public endpoint
await client.tournaments.getPublicList(); // Available to all
```

4. **Contact admin** if role assignment is incorrect.

---

### Error: `500 Internal Server Error`

**Symptom:**

```json
{ "detail": "Internal server error." }
```

**Likely Cause:**

- Backend bug
- Database issue
- Unhandled exception in backend code

**How to Fix:**

1. **Check backend logs** (if you have access):

```powershell
# In backend directory
tail -f logs/django.log
```

2. **Report to backend team** with:
   - Request URL
   - Request body (if POST/PATCH)
   - Timestamp
   - Steps to reproduce

3. **Workaround**: Use mock data or skip the failing request temporarily.

---

## Tailwind & Styling Issues

### Issue: Tailwind styles not applying

**Symptom:**

Classes like `bg-blue-500` or `p-4` have no effect.

**Likely Cause:**

- Tailwind config missing or incorrect
- PostCSS not configured
- Dev server needs restart

**How to Fix:**

1. **Check `tailwind.config.js`** exists in the frontend directory:

```javascript
// tailwind.config.js
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      // Design tokens here
    },
  },
  plugins: [],
};
```

2. **Verify `postcss.config.js`**:

```javascript
// postcss.config.js
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

3. **Check global CSS** imports Tailwind directives:

```css
/* styles/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;
```

4. **Restart the dev server**:

```powershell
# Ctrl+C to stop, then:
pnpm dev
```

5. **Clear Next.js cache**:

```powershell
Remove-Item -Recurse -Force .next
pnpm dev
```

---

### Issue: Custom design tokens not working

**Symptom:**

Classes like `text-brand-primary` or `bg-semantic-success` don't work.

**Likely Cause:**

- Design tokens not loaded into Tailwind config
- Typo in class name

**How to Fix:**

1. **Check Tailwind config** extends design tokens:

```javascript
// tailwind.config.js
const designTokens = require('./design-tokens.json');

module.exports = {
  theme: {
    extend: {
      colors: designTokens.colors,
      spacing: designTokens.spacing,
      // ...
    },
  },
};
```

2. **Verify `design-tokens.json`** exists:

```powershell
ls design-tokens.json
```

If missing, copy from `Documents/Modify_TournamentApp/Frontend/design-tokens.json`.

3. **Test a token manually**:

```tsx
<div className="text-brand-primary">Test</div>
```

If color doesn't apply, check the token name in `design-tokens.json`:

```json
{
  "colors": {
    "brand": {
      "primary": "#3B82F6"
    }
  }
}
```

4. **Restart dev server** after config changes.

---

### Issue: Styles flash then disappear (FOUC)

**Symptom:**

Page loads with correct styles, then they disappear briefly.

**Likely Cause:**

- CSS not extracted correctly in production build
- Next.js hydration mismatch

**How to Fix:**

1. **Check for hydration errors** in console:

```
Warning: Text content did not match. Server: "X" Client: "Y"
```

Fix mismatches between server and client rendering.

2. **Ensure CSS is imported** in `app/layout.tsx`:

```typescript
import '@/styles/globals.css';
```

3. **Rebuild**:

```powershell
pnpm build
pnpm start
```

If the issue persists in production build, it's a hydration problem.

---

## Design Tokens Not Loading

### Issue: `design-tokens.json` not found

**Symptom:**

```
Module not found: Can't resolve './design-tokens.json'
```

**Likely Cause:**

- File is missing or in the wrong location

**How to Fix:**

1. **Check file location**:

```powershell
ls Documents/Modify_TournamentApp/Frontend/design-tokens.json
```

2. **Copy from source** (if missing):

```powershell
Copy-Item static/design-tokens.json Documents/Modify_TournamentApp/Frontend/
```

3. **Update Tailwind config path** (if file is elsewhere):

```javascript
const designTokens = require('./path/to/design-tokens.json');
```

---

### Issue: Token values incorrect

**Symptom:**

Color is wrong (e.g., expecting blue, seeing red).

**Likely Cause:**

- Token definition is incorrect
- Wrong token name used

**How to Fix:**

1. **Check token definition**:

```json
// design-tokens.json
{
  "colors": {
    "brand": {
      "primary": "#3B82F6" // ← Verify this value
    }
  }
}
```

2. **Check class name**:

```tsx
<div className="text-brand-primary"> {/* Correct */}
<div className="text-primary"> {/* ❌ Wrong */}
```

3. **Inspect in DevTools**:

Right-click element → Inspect → Check computed styles.

---

## Backend Connection Issues

### Issue: Can't connect to local backend

**Symptom:**

Requests to `http://localhost:8000` fail with `ECONNREFUSED`.

**Likely Cause:**

- Backend is not running
- Wrong port

**How to Fix:**

1. **Start the backend**:

```powershell
cd G:\My Projects\WORK\DeltaCrown
python manage.py runserver
```

2. **Check the port**:

```
Django version 4.x.x, using settings 'deltacrown.settings'
Starting development server at http://127.0.0.1:8000/
```

If backend runs on a different port (e.g., 8001), update `.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8001
```

3. **Test manually**:

```powershell
curl http://localhost:8000/api/schema/
```

---

### Issue: CORS errors with local backend

**Symptom:**

```
Access to fetch at 'http://localhost:8000/api/...' from origin 'http://localhost:3000' has been blocked by CORS policy.
```

**Likely Cause:**

- Backend CORS settings don't allow `localhost:3000`

**How to Fix:**

1. **Check backend CORS config** (`deltacrown/settings.py`):

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

2. **Install `django-cors-headers`** (if not installed):

```powershell
pip install django-cors-headers
```

3. **Add to `INSTALLED_APPS`**:

```python
INSTALLED_APPS = [
    # ...
    'corsheaders',
]
```

4. **Add middleware**:

```python
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    # ...
]
```

5. **Restart backend**:

```powershell
python manage.py runserver
```

---

## Dependency & Version Mismatches

### Issue: `npm ERR! peer dependency` warnings

**Symptom:**

```
npm WARN ERESOLVE overriding peer dependency
```

**Likely Cause:**

- Dependency version conflicts

**How to Fix:**

1. **Use pnpm** (handles peer deps better):

```powershell
npm install -g pnpm
Remove-Item -Recurse -Force node_modules
pnpm install
```

2. **Or use `--legacy-peer-deps`** (npm):

```powershell
npm install --legacy-peer-deps
```

3. **Check for outdated packages**:

```powershell
pnpm outdated
```

Update major versions carefully (may break things).

---

### Issue: Node version mismatch

**Symptom:**

```
error [email protected]: The engine "node" is incompatible with this module.
```

**Likely Cause:**

- Node version is too old or too new

**How to Fix:**

1. **Check required version** in `package.json`:

```json
"engines": {
  "node": ">=18.0.0"
}
```

2. **Check your version**:

```powershell
node --version
```

3. **Switch to correct version** (using nvm):

```powershell
nvm install 20
nvm use 20
```

4. **Reinstall dependencies**:

```powershell
Remove-Item -Recurse -Force node_modules
pnpm install
```

---

## Build & Compilation Errors

### Error: `Module parse failed: Unexpected token`

**Symptom:**

```
Module parse failed: Unexpected token (1:0)
You may need an appropriate loader to handle this file type.
```

**Likely Cause:**

- Importing a file Next.js doesn't know how to process (e.g., `.svg`, `.json` incorrectly)

**How to Fix:**

1. **Check import statement**:

```typescript
// ❌ Wrong
import data from './data.json';

// ✅ Correct
import data from './data.json' assert { type: 'json' };
```

2. **For SVGs**, use `next/image` or SVGR:

```typescript
import Image from 'next/image';
<Image src="/logo.svg" alt="Logo" width={100} height={100} />
```

3. **Check file extension** is correct.

---

### Error: `ReferenceError: window is not defined`

**Symptom:**

```
ReferenceError: window is not defined
```

**Likely Cause:**

- Accessing browser-only APIs (`window`, `document`, `localStorage`) in a Server Component

**How to Fix:**

1. **Use Client Component** for browser APIs:

```typescript
'use client';

export default function MyComponent() {
  const token = localStorage.getItem('token'); // ✅ OK in Client Component
  // ...
}
```

2. **Or guard the access**:

```typescript
const token = typeof window !== 'undefined' 
  ? localStorage.getItem('token') 
  : null;
```

3. **Move browser logic to `useEffect`**:

```typescript
useEffect(() => {
  const token = localStorage.getItem('token');
  // ...
}, []);
```

---

## Runtime Errors

### Error: `Hydration failed` or `Text content does not match`

**Symptom:**

```
Warning: Text content did not match. Server: "Loading..." Client: "Data loaded"
```

**Likely Cause:**

- Server and client render different content
- Using `Date.now()` or random values

**How to Fix:**

1. **Ensure consistent rendering**:

```typescript
// ❌ Wrong: Date changes between server and client
<div>{new Date().toLocaleString()}</div>

// ✅ Correct: Use state updated on client
const [time, setTime] = useState('');
useEffect(() => {
  setTime(new Date().toLocaleString());
}, []);
<div>{time || 'Loading...'}</div>
```

2. **Suppress hydration warning** (if intentional):

```tsx
<div suppressHydrationWarning>{new Date().toLocaleString()}</div>
```

---

### Error: `Maximum update depth exceeded`

**Symptom:**

```
Error: Maximum update depth exceeded. This can happen when a component repeatedly calls setState inside componentWillUpdate or componentDidUpdate.
```

**Likely Cause:**

- Infinite re-render loop (e.g., setState in render)

**How to Fix:**

1. **Check for setState in render**:

```typescript
// ❌ Wrong
function MyComponent() {
  const [count, setCount] = useState(0);
  setCount(count + 1); // ← Infinite loop!
  return <div>{count}</div>;
}

// ✅ Correct
function MyComponent() {
  const [count, setCount] = useState(0);
  useEffect(() => {
    setCount(count + 1);
  }, []); // Only once on mount
  return <div>{count}</div>;
}
```

2. **Check useEffect dependencies**:

```typescript
useEffect(() => {
  setData(fetchData()); // ← Causes re-render
}, [data]); // ← Re-runs on every render! Infinite loop.

// ✅ Fix: Remove `data` from deps or add condition
useEffect(() => {
  if (!data) setData(fetchData());
}, [data]);
```

---

## Performance Issues

### Issue: Slow page load

**Symptom:**

Pages take 5+ seconds to load.

**Likely Cause:**

- Large bundle size
- Too many API requests
- Unoptimized images

**How to Fix:**

1. **Analyze bundle size**:

```powershell
pnpm build
```

Look for large chunks:

```
Route (app)                              Size     First Load JS
┌ ○ /tournaments                         **42 kB**        120 kB
```

If a route has >100 kB, optimize it.

2. **Use dynamic imports** for heavy components:

```typescript
import dynamic from 'next/dynamic';

const HeavyComponent = dynamic(() => import('./HeavyComponent'), {
  loading: () => <LoadingSpinner />,
});
```

3. **Reduce API requests**: Use React Query caching:

```typescript
const { data } = useQuery({
  queryKey: ['tournaments'],
  queryFn: () => client.tournaments.list(),
  staleTime: 5 * 60 * 1000, // Cache for 5 minutes
});
```

4. **Optimize images**: Use `next/image`:

```tsx
import Image from 'next/image';
<Image src="/banner.jpg" alt="Banner" width={800} height={400} />
```

---

### Issue: UI freezes during data fetch

**Symptom:**

UI becomes unresponsive while loading data.

**Likely Cause:**

- Synchronous blocking operation
- Too much data rendering at once

**How to Fix:**

1. **Use async/await properly**:

```typescript
// ❌ Wrong: Blocking
const data = fetchDataSync(); // Freezes UI

// ✅ Correct: Non-blocking
const { data, isLoading } = useQuery({
  queryKey: ['data'],
  queryFn: fetchDataAsync,
});
```

2. **Virtualize long lists** (e.g., 1000+ items):

```typescript
import { useVirtualizer } from '@tanstack/react-virtual';

const rowVirtualizer = useVirtualizer({
  count: items.length,
  getScrollElement: () => parentRef.current,
  estimateSize: () => 50,
});
```

3. **Paginate** instead of loading all data:

```typescript
const { data } = useQuery({
  queryKey: ['tournaments', page],
  queryFn: () => client.tournaments.list({ page, page_size: 20 }),
});
```

---

## When to Ask for Help

If none of the above solutions work, it's time to ask for help. **Before you do**, gather the following information:

### What to Include in Your Request

1. **Symptom**: Clear description of what's wrong
   - ❌ "It doesn't work"
   - ✅ "The tournaments page shows a blank screen after login"

2. **Error messages**: Copy the FULL error from console/terminal
   ```
   TypeError: Cannot read property 'name' of undefined
   at TournamentsPage (app/tournaments/page.tsx:42:15)
   ```

3. **Steps to reproduce**:
   1. Login as organizer
   2. Navigate to `/tournaments`
   3. Click "Create Tournament"
   4. Error appears

4. **Environment info**:
   - Node version: `node --version`
   - Package manager: pnpm/npm/yarn
   - OS: Windows/macOS/Linux
   - Browser: Chrome/Firefox/Safari

5. **What you've tried**:
   - "Restarted dev server"
   - "Re-linked SDK"
   - "Checked `.env.local`"

6. **Relevant code** (if applicable):
   ```typescript
   const tournament = await client.tournaments.get(id);
   console.log(tournament.name); // ← Error here
   ```

7. **Screenshots** (if visual issue):
   - Browser console
   - DevTools Network tab
   - UI showing the problem

---

### Where to Ask

- **Team Slack/Discord**: For quick questions
- **GitHub Issues**: For bugs or feature requests
- **Code review**: If you suspect the issue is in your PR

---

### What NOT to Ask

- ❌ "Why isn't it working?" (too vague)
- ❌ "Can you fix this?" (without context)
- ❌ "It's broken" (no details)

Always provide **specific details** and **what you've tried**.

---

## Additional Resources

- **Setup Guide**: [LOCAL_SETUP.md](./LOCAL_SETUP.md)
- **SDK Documentation**: [SDK_USAGE_GUIDE.md](./SDK_USAGE_GUIDE.md)
- **API Reference**: [API_REFERENCE.md](./API_REFERENCE.md)
- **Component Library**: [COMPONENTS_GUIDE.md](./COMPONENTS_GUIDE.md)

For architectural questions, see [INTRODUCTION.md](./INTRODUCTION.md).

---

**Good luck debugging! 🐛🔨**
