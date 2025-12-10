# Local Development Setup

## Table of Contents

1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Clone & Install](#clone--install)
4. [Environment Variables](#environment-variables)
5. [Development Scripts](#development-scripts)
6. [First Sanity Check](#first-sanity-check)
7. [Common Issues](#common-issues)
8. [Next Steps](#next-steps)

---

## Introduction

This guide walks new frontend developers through setting up the **DeltaCrown Organizer Console** on their local machine. By the end of this guide, you'll have:

- ✅ A working local development environment
- ✅ The frontend SDK installed and linked
- ✅ Environment variables configured
- ✅ The dev server running
- ✅ A fully functional dashboard in your browser

**Time estimate**: 15–30 minutes (depending on internet speed and system setup)

---

## Prerequisites

Before you begin, ensure you have the following installed:

### 1. Node.js

**Required version**: Node.js **18.x or higher** (recommended: 20.x LTS)

**Check your version:**

```powershell
node --version
```

**Install/Update:**

Download from [nodejs.org](https://nodejs.org/) or use a version manager:

- **Windows**: [nvm-windows](https://github.com/coreybutler/nvm-windows)
- **macOS/Linux**: [nvm](https://github.com/nvm-sh/nvm)

```bash
# Using nvm (macOS/Linux)
nvm install 20
nvm use 20

# Using nvm-windows (Windows)
nvm install 20
nvm use 20
```

---

### 2. Package Manager

The project supports **npm**, **pnpm**, or **yarn**. We recommend **pnpm** for faster installs and better disk usage.

**Check if you have pnpm:**

```powershell
pnpm --version
```

**Install pnpm (if needed):**

```powershell
npm install -g pnpm
```

**Alternatively, use npm** (comes with Node.js):

```powershell
npm --version
```

---

### 3. Backend API (Optional but Recommended)

The frontend requires a running backend API to function fully. You have two options:

**Option A: Use the staging/development backend**

- Base URL: `https://api-staging.deltacrown.example.com`
- Provided by the backend team
- No local setup required
- **Use this if you only need frontend development**

**Option B: Run the backend locally**

- Requires Python, PostgreSQL, Redis
- See backend setup docs (not covered here)
- **Use this if you need to test API changes or work on full-stack features**

For **frontend-only development**, **Option A is recommended**.

---

### 4. Git

Ensure Git is installed:

```powershell
git --version
```

Download from [git-scm.com](https://git-scm.com/) if needed.

---

## Clone & Install

### Step 1: Clone the Repository

```powershell
git clone https://github.com/your-org/DeltaCrown.git
cd DeltaCrown
```

**Navigate to the frontend directory:**

```powershell
cd Documents/Modify_TournamentApp/Frontend
```

> **Note**: The frontend code lives in `Documents/Modify_TournamentApp/Frontend/`, not in the repository root.

---

### Step 2: Install Dependencies

Using **pnpm** (recommended):

```powershell
pnpm install
```

Using **npm**:

```powershell
npm install
```

Using **yarn**:

```powershell
yarn install
```

**What this does:**

- Installs all packages listed in `package.json`
- Creates `node_modules/` directory
- Generates a lockfile (`pnpm-lock.yaml`, `package-lock.json`, or `yarn.lock`)

**Time estimate**: 2–5 minutes

---

### Step 3: Install/Link the SDK

The **DeltaCrown SDK** (Epic 9.2) is a TypeScript package that provides type-safe API access. It's located in the repository at:

```
G:\My Projects\WORK\DeltaCrown\frontend_sdk\
```

You have two options for using the SDK:

#### Option A: Link the SDK locally (recommended for development)

This creates a symlink so changes to the SDK are immediately reflected in the frontend.

**In the SDK directory:**

```powershell
cd ../../../frontend_sdk
pnpm link --global
```

**Back in the frontend directory:**

```powershell
cd ../Documents/Modify_TournamentApp/Frontend
pnpm link --global deltacrown-sdk
```

> **npm/yarn users**: Replace `pnpm` with `npm` or `yarn` in the commands above.

**Verify the link:**

```powershell
ls node_modules/deltacrown-sdk
```

You should see the SDK files. If it's a symlink, the path will show the original SDK directory.

---

#### Option B: Install the SDK as a published package

If the SDK is published to npm (or a private registry), you can install it directly:

```powershell
pnpm add deltacrown-sdk
```

**When to use this:**

- SDK is published to npm
- You don't need to modify SDK code
- You want to lock to a specific SDK version

---

### Step 4: Verify Installation

Check that all dependencies installed correctly:

```powershell
pnpm list --depth=0
```

You should see:

- `next` (Next.js framework)
- `react`, `react-dom` (React 18+)
- `@tanstack/react-query` (data fetching)
- `tailwindcss` (styling)
- `deltacrown-sdk` (API client)
- Other dependencies

---

## Environment Variables

Next.js uses **environment variables** for configuration. Create a `.env.local` file in the frontend directory to store local settings.

### Step 1: Create `.env.local`

**In the frontend directory:**

```powershell
cd Documents/Modify_TournamentApp/Frontend
New-Item .env.local -ItemType File
```

> **Note**: `.env.local` is gitignored and should **never** be committed.

---

### Step 2: Add Required Variables

Open `.env.local` in your editor and add:

```bash
# API Configuration
NEXT_PUBLIC_API_BASE_URL=https://api-staging.deltacrown.example.com

# Authentication (optional, for testing)
# NEXT_PUBLIC_AUTH_TOKEN=your_test_token_here

# Feature Flags (optional)
# NEXT_PUBLIC_ENABLE_ANALYTICS=true
```

**Variable Explanations:**

| Variable                      | Description                                    | Required | Example                                       |
| ----------------------------- | ---------------------------------------------- | -------- | --------------------------------------------- |
| `NEXT_PUBLIC_API_BASE_URL`    | Base URL of the backend API                    | ✅ Yes   | `https://api-staging.deltacrown.example.com`  |
| `NEXT_PUBLIC_AUTH_TOKEN`      | Pre-set auth token for testing (dev only)      | ❌ No    | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`     |
| `NEXT_PUBLIC_ENABLE_ANALYTICS`| Enable/disable analytics tracking             | ❌ No    | `true` or `false`                             |

> **`NEXT_PUBLIC_` prefix**: Variables starting with `NEXT_PUBLIC_` are exposed to the browser. Do NOT use this prefix for secrets (API keys, database URLs, etc.).

---

### Step 3: Local Backend (Optional)

If running the backend locally, update the API URL:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

> **Note**: Ensure the backend is running on port 8000 (or update the URL to match your backend port).

---

### Step 4: Verify Environment Variables

Start the dev server (see next section) and check the console:

```typescript
// In any component or page
console.log('API Base URL:', process.env.NEXT_PUBLIC_API_BASE_URL);
```

You should see your configured URL in the browser console.

---

## Development Scripts

The `package.json` includes several scripts for development, building, and testing.

### Start Development Server

**Run the Next.js dev server:**

```powershell
pnpm dev
```

**What this does:**

- Starts Next.js in development mode
- Enables hot module replacement (HMR)
- Runs on `http://localhost:3000` by default
- Watches for file changes and auto-reloads

**Output:**

```
> deltacrown-frontend@0.1.0 dev
> next dev

   ▲ Next.js 14.x.x
   - Local:        http://localhost:3000
   - Network:      http://192.168.x.x:3000

 ✓ Ready in 2.5s
```

**Open in browser**: [http://localhost:3000](http://localhost:3000)

---

### Build for Production

**Create an optimized production build:**

```powershell
pnpm build
```

**What this does:**

- Compiles TypeScript
- Bundles JavaScript/CSS
- Optimizes images
- Generates static pages where possible
- Creates `.next/` directory with build output

**Output:**

```
Route (app)                              Size     First Load JS
┌ ○ /                                    142 B          87.3 kB
├ ○ /tournaments                         2.1 kB         89.4 kB
├ ○ /tournaments/[id]                    1.8 kB         88.9 kB
└ ○ /scheduling                          1.5 kB         88.6 kB

○  (Static)  automatically rendered as static HTML
```

---

### Start Production Server

**Run the production build locally:**

```powershell
pnpm start
```

**What this does:**

- Serves the production build from `.next/`
- Runs on `http://localhost:3000`
- No hot reload (requires rebuild for changes)

**Use this to:**

- Test production behavior locally
- Verify build optimization
- Debug production-only issues

---

### Lint Code

**Check for code quality issues:**

```powershell
pnpm lint
```

**What this does:**

- Runs ESLint on TypeScript/React files
- Checks for syntax errors, unused variables, etc.
- Reports warnings and errors

**Fix auto-fixable issues:**

```powershell
pnpm lint --fix
```

---

### Run Tests (if configured)

**Run unit/integration tests:**

```powershell
pnpm test
```

> **Note**: Test setup may vary. Check `package.json` for configured test runner (Jest, Vitest, etc.).

---

### Format Code (if Prettier configured)

**Format all files:**

```powershell
pnpm format
```

Or manually run Prettier:

```powershell
pnpx prettier --write .
```

---

## First Sanity Check

After starting the dev server, verify everything works correctly.

### Step 1: Open the Dashboard

Navigate to: [http://localhost:3000](http://localhost:3000)

**Expected behavior:**

- Dashboard page loads
- You see the organizer console UI
- Navigation sidebar appears
- No errors in the browser console

---

### Step 2: Check Browser Console

Open **DevTools** (F12 or Ctrl+Shift+I) and check the **Console** tab.

**✅ Good signs:**

- No red errors
- API requests succeed (or fail gracefully with auth errors if not logged in)
- Component renders correctly

**⚠️ Common warnings (safe to ignore for now):**

- `Warning: Extra attributes from the server` (Next.js hydration, usually harmless)
- `[Fast Refresh] rebuilding` (expected during development)

**❌ Red flags:**

- `Failed to fetch` or `Network error` → Backend not reachable (check `NEXT_PUBLIC_API_BASE_URL`)
- `Module not found` → Dependency issue (re-run `pnpm install`)
- `Unexpected token` or syntax errors → Check for typos in recent code changes

---

### Step 3: Check Network Tab

Open the **Network** tab in DevTools and refresh the page.

**Look for:**

- API requests to `/api/tournaments/`, `/api/auth/`, etc.
- Status codes:
  - `200 OK` → Success
  - `401 Unauthorized` → Expected if not logged in
  - `404 Not Found` → Check API URL
  - `500 Internal Server Error` → Backend issue

**Example request:**

```
Request URL: https://api-staging.deltacrown.example.com/api/tournaments/v1/organizer/tournaments/
Status: 401 Unauthorized
```

> This is **normal** if you're not authenticated yet. See [WORKFLOW_GUIDE.md](./WORKFLOW_GUIDE.md) for login flow.

---

### Step 4: Test Navigation

Click around the UI:

- **Dashboard** → Should load stats (or empty state if not logged in)
- **Tournaments** → Should show tournament list or login prompt
- **Scheduling** → Should load calendar view
- **Results** → Should load results inbox

**All pages should load without crashing.**

---

### Step 5: Check Terminal Output

Look at the terminal where you ran `pnpm dev`:

**✅ Good:**

```
 ✓ Compiled /tournaments in 523ms
 ✓ Compiled /dashboard in 341ms
```

**❌ Bad:**

```
 ✗ Failed to compile
./app/tournaments/page.tsx
Type error: Property 'name' does not exist on type 'Tournament'.
```

If you see TypeScript errors, fix them before proceeding.

---

## Common Issues

### Issue 1: `command not found: pnpm`

**Cause**: pnpm is not installed globally.

**Fix**:

```powershell
npm install -g pnpm
```

---

### Issue 2: `ENOENT: no such file or directory, open '.env.local'`

**Cause**: `.env.local` file is missing.

**Fix**:

Create the file:

```powershell
New-Item .env.local -ItemType File
```

Add required variables (see [Environment Variables](#environment-variables)).

---

### Issue 3: `Failed to fetch` or `Network Error`

**Cause**: Backend API is not reachable.

**Fix**:

1. Check `NEXT_PUBLIC_API_BASE_URL` in `.env.local`
2. Verify the backend is running (if local) or the staging URL is correct
3. Check for CORS issues (backend must allow `http://localhost:3000`)

**Test the API manually:**

```powershell
curl https://api-staging.deltacrown.example.com/api/schema/
```

You should get JSON response (OpenAPI schema).

---

### Issue 4: `Module not found: Can't resolve 'deltacrown-sdk'`

**Cause**: SDK is not installed or linked.

**Fix**:

Re-link the SDK:

```powershell
cd ../../../frontend_sdk
pnpm link --global
cd ../Documents/Modify_TournamentApp/Frontend
pnpm link --global deltacrown-sdk
```

Or install from npm:

```powershell
pnpm add deltacrown-sdk
```

---

### Issue 5: Port 3000 already in use

**Cause**: Another process is using port 3000.

**Fix**:

Kill the process or use a different port:

```powershell
# Use a different port
pnpm dev -- -p 3001
```

Open [http://localhost:3001](http://localhost:3001).

---

### Issue 6: Tailwind styles not applying

**Cause**: Tailwind config may be misconfigured or PostCSS not running.

**Fix**:

1. Verify `tailwind.config.js` exists in the frontend directory
2. Check `postcss.config.js` includes Tailwind plugin
3. Restart the dev server (`Ctrl+C`, then `pnpm dev`)

**Test Tailwind:**

Add a test class to any component:

```tsx
<div className="bg-red-500 p-4">Test</div>
```

If you see a red box with padding, Tailwind is working.

---

### Issue 7: TypeScript errors on build

**Cause**: Type mismatches or missing type definitions.

**Fix**:

1. Run the type checker:

```powershell
pnpm tsc --noEmit
```

2. Fix reported errors (missing imports, incorrect types, etc.)
3. Rebuild:

```powershell
pnpm build
```

---

### Issue 8: `node:events:492 throw er; // Unhandled 'error' event`

**Cause**: Node.js version mismatch or corrupted `node_modules`.

**Fix**:

1. Check Node version (must be 18+):

```powershell
node --version
```

2. Delete `node_modules` and reinstall:

```powershell
Remove-Item -Recurse -Force node_modules
pnpm install
```

3. Clear Next.js cache:

```powershell
Remove-Item -Recurse -Force .next
pnpm dev
```

---

## Next Steps

Now that your local environment is set up, explore the codebase:

1. **Read the architecture guide**: [INTRODUCTION.md](./INTRODUCTION.md)
2. **Understand the project structure**: [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)
3. **Learn the SDK**: [SDK_USAGE_GUIDE.md](./SDK_USAGE_GUIDE.md)
4. **Explore components**: [COMPONENTS_GUIDE.md](./COMPONENTS_GUIDE.md)
5. **See workflows in action**: [WORKFLOW_GUIDE.md](./WORKFLOW_GUIDE.md)

**Start coding:**

- Create a new page in `app/`
- Build a component in `components/`
- Add SDK integration in a Server Component
- Style with Tailwind using design tokens

**Need help?**

- Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues
- Ask in the team Slack/Discord
- Open an issue on GitHub

---

**Happy coding! 🚀**
