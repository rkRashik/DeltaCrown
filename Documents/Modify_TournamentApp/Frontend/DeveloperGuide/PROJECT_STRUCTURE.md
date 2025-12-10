# DeltaCrown Frontend Project Structure

**Complete guide to the frontend repository organization**

This document provides a comprehensive map of the DeltaCrown frontend codebase, explaining the purpose of each directory, file naming conventions, and how the structure supports the Epic 9.4 boilerplate architecture.

---

## Table of Contents

1. [High-Level Overview](#high-level-overview)
2. [Root Directory Structure](#root-directory-structure)
3. [App Directory (`app/`)](#app-directory-app)
4. [Components Directory (`components/`)](#components-directory-components)
5. [Providers Directory (`providers/`)](#providers-directory-providers)
6. [Hooks Directory (`hooks/`)](#hooks-directory-hooks)
7. [Library Directory (`lib/`)](#library-directory-lib)
8. [Styles Directory (`styles/`)](#styles-directory-styles)
9. [Frontend SDK (`frontend_sdk/`)](#frontend-sdk-frontend_sdk)
10. [Documentation (`Frontend/` and `DeveloperGuide/`)](#documentation-frontend-and-developerguide)
11. [File Naming Conventions](#file-naming-conventions)
12. [Best Practices](#best-practices)
13. [Do's and Don'ts](#dos-and-donts)

---

## High-Level Overview

The DeltaCrown frontend follows **Next.js 14+ App Router** conventions with a domain-driven folder structure:

```
Documents/Modify_TournamentApp/Frontend/
├── app/                          # Next.js App Router pages and layouts
│   ├── layout.tsx                # Root layout with providers
│   ├── page.tsx                  # Dashboard (homepage)
│   ├── tournaments/              # Tournament routes
│   ├── matches/                  # Match management routes
│   ├── staff/                    # Staff management routes
│   ├── scheduling/               # Match scheduling routes
│   ├── results/                  # Results inbox routes
│   ├── analytics/                # Analytics dashboard routes
│   └── help/                     # Help documentation routes
│
├── components/                   # Reusable UI components
│   ├── Header.tsx                # Top navigation bar
│   ├── Sidebar.tsx               # Organizer sidebar navigation
│   ├── UserMenu.tsx              # User dropdown menu
│   ├── Card.tsx                  # Card container component
│   ├── Button.tsx                # Button component
│   ├── Input.tsx                 # Form input component
│   ├── Select.tsx                # Dropdown select component
│   ├── Modal.tsx                 # Modal dialog component
│   ├── Tabs.tsx                  # Tab navigation component
│   ├── Badge.tsx                 # Status badge component
│   ├── Table.tsx                 # Data table component
│   ├── EmptyState.tsx            # Empty state placeholder
│   ├── StatCard.tsx              # Statistics card (data component)
│   ├── LeaderboardTable.tsx      # Leaderboard display (data component)
│   ├── MatchCard.tsx             # Match card (data component)
│   └── TournamentCard.tsx        # Tournament card (data component)
│
├── providers/                    # React Context providers
│   ├── ThemeProvider.tsx         # Dark/light mode management
│   ├── AuthProvider.tsx          # Authentication state
│   ├── QueryProvider.tsx         # React Query configuration
│   └── ToastProvider.tsx         # Global notifications
│
├── hooks/                        # Custom React hooks
│   ├── useDebounce.ts            # Debounce value updates
│   ├── useLocalStorage.ts        # Persist state to localStorage
│   └── useMediaQuery.ts          # Responsive breakpoint detection
│
├── lib/                          # Utility functions and helpers
│   ├── cn.ts                     # Conditional classname utility
│   ├── formatters.ts             # Date/currency/number formatters
│   └── api.ts                    # DeltaCrown SDK wrapper
│
├── styles/                       # Global styles and CSS
│   └── globals.css               # Global CSS with design tokens
│
├── design-tokens.json            # Design system tokens (Epic 9.3)
├── tailwind.config.js            # Tailwind CSS configuration
│
└── DeveloperGuide/               # Developer documentation (Epic 9.5)
    ├── INTRODUCTION.md
    ├── PROJECT_STRUCTURE.md      # This file
    ├── SDK_USAGE_GUIDE.md
    ├── COMPONENTS_GUIDE.md
    └── ... (other guides)
```

**Additional Directories (Not in Frontend folder):**

```
frontend_sdk/                     # TypeScript SDK from Epic 9.2
├── package.json
├── tsconfig.json
├── src/
│   ├── types/                    # Auto-generated + curated types
│   ├── client/                   # DeltaCrownClient class
│   └── endpoints/                # Endpoint configuration
└── tests/                        # SDK tests
```

---

## Root Directory Structure

### Location
```
Documents/Modify_TournamentApp/Frontend/
```

### Purpose
Contains all frontend-specific code, documentation, and configuration files created in **Phase 9** (Epics 9.3, 9.4, 9.5).

### Key Files

#### `design-tokens.json` (Epic 9.3)
**Purpose:** Centralized design system tokens (colors, typography, spacing, shadows, borders, transitions).

**Example:**
```json
{
  "colors": {
    "brand": {
      "primary": "#3B82F6",
      "secondary": "#8B5CF6"
    },
    "semantic": {
      "success": "#10B981",
      "error": "#EF4444"
    }
  },
  "typography": {
    "fontFamily": {
      "sans": "Inter, system-ui, sans-serif"
    }
  }
}
```

**Usage:**
- Referenced by `tailwind.config.js`
- Consumed through Tailwind utility classes (`bg-primary-500`, `text-heading-lg`)

#### `tailwind.config.js` (Epic 9.3)
**Purpose:** Extends Tailwind CSS with design tokens.

**Example:**
```javascript
module.exports = {
  content: ['./app/**/*.{js,ts,jsx,tsx}', './components/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: require('./design-tokens.json').colors,
      spacing: require('./design-tokens.json').spacing,
    }
  }
}
```

---

## App Directory (`app/`)

### Purpose
Contains **Next.js App Router** pages, layouts, and route handlers. This is the **entry point** for all routes in the application.

### Convention
- **File-based routing:** Each folder becomes a route segment
- **Special files:**
  - `layout.tsx` — Shared UI wrapper for child routes
  - `page.tsx` — Route endpoint (renders the page)
  - `loading.tsx` — Loading UI (automatic Suspense boundary)
  - `error.tsx` — Error UI (automatic error boundary)

### Structure

```
app/
├── layout.tsx                    # Root layout (wraps entire app)
├── page.tsx                      # Dashboard page (/)
│
├── tournaments/
│   ├── page.tsx                  # Tournament list (/tournaments)
│   └── [id]/
│       └── page.tsx              # Tournament detail (/tournaments/:id)
│
├── matches/
│   ├── page.tsx                  # Match list (/matches)
│   └── [id]/
│       └── page.tsx              # Match detail (/matches/:id)
│
├── staff/
│   ├── page.tsx                  # Staff list (/staff)
│   └── [id]/
│       └── page.tsx              # Staff detail (/staff/:id)
│
├── scheduling/
│   └── page.tsx                  # Match scheduling (/scheduling)
│
├── results/
│   └── page.tsx                  # Results inbox (/results)
│
├── analytics/
│   └── page.tsx                  # Analytics dashboard (/analytics)
│
└── help/
    └── page.tsx                  # Help center (/help)
```

### File Details

#### `app/layout.tsx` (Root Layout)
**Purpose:** Wraps the entire application with global providers and navigation.

**Key Features:**
- Metadata configuration (title, description, viewport)
- Font loading (Inter, Geist Sans/Mono)
- Provider stack (Theme → Auth → Query → Toast)
- Persistent navigation (Header + Sidebar)

**Example:**
```tsx
import { ThemeProvider } from '@/providers/ThemeProvider';
import { AuthProvider } from '@/providers/AuthProvider';
import { QueryProvider } from '@/providers/QueryProvider';
import { ToastProvider } from '@/providers/ToastProvider';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <AuthProvider>
            <QueryProvider>
              <ToastProvider>
                <Header />
                <div className="flex">
                  <Sidebar />
                  <main className="flex-1">{children}</main>
                </div>
              </ToastProvider>
            </QueryProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
```

#### `app/page.tsx` (Dashboard)
**Purpose:** Main organizer dashboard with tournament overview, stats, recent matches.

**Key Features:**
- 4 StatCards (Active Tournaments, Participants, Pending Matches, Revenue)
- Active tournaments grid (TournamentCard components)
- Recent matches list (MatchCard components)

**Example:**
```tsx
export default async function DashboardPage() {
  // TODO: Replace with SDK call in Epic 9.2 integration
  const stats = await client.analytics.getOrganizerDashboard();
  const tournaments = await client.tournaments.list({ status: 'in_progress' });
  const matches = await client.matches.list({ limit: 5 });

  return (
    <div>
      <h1>Dashboard</h1>
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Active Tournaments" value={stats.active_tournaments} />
        {/* ... more stats */}
      </div>
      
      <TournamentGrid tournaments={tournaments} />
      <MatchList matches={matches} />
    </div>
  );
}
```

#### `app/tournaments/page.tsx` (Tournament List)
**Purpose:** Browse and filter tournaments, create new tournaments.

**Key Features:**
- Search input (tournament name)
- Status filter dropdown (draft, open, in-progress, completed)
- Create Tournament button
- Tournament grid with TournamentCard components

#### `app/tournaments/[id]/page.tsx` (Tournament Detail)
**Purpose:** View tournament details with tabs (Overview, Leaderboard, Matches, Bracket).

**Key Features:**
- Tournament header (name, status badge, game, format)
- Tabs component for navigation
- Leaderboard with LeaderboardTable
- Match list with MatchCard components
- Bracket visualization (placeholder)

#### Dynamic Routes (`[id]`)
**Convention:** Square brackets indicate **dynamic route segments**.

**Example:**
```
app/tournaments/[id]/page.tsx  →  /tournaments/123
app/matches/[id]/page.tsx      →  /matches/456
```

**Accessing Params:**
```tsx
export default async function TournamentDetailPage({ params }: { params: { id: string } }) {
  const tournament = await client.tournaments.get(params.id);
  return <div>{tournament.name}</div>;
}
```

---

## Components Directory (`components/`)

### Purpose
Houses **all reusable React components** used across pages. Components are organized by type (navigation, UI primitives, data display).

### Organizational Strategy

**Flat Structure (Current):**
All components in root `components/` folder for simplicity.

**Future Scalability:**
Consider organizing into subdirectories:
```
components/
├── navigation/      # Header, Sidebar, UserMenu
├── ui/              # Button, Input, Card, Modal (primitives)
├── data/            # TournamentCard, MatchCard, StatCard (domain-specific)
└── layout/          # Grid, Container, Section (layout helpers)
```

### Component Categories

#### 1. Navigation Components

**Header.tsx**
- Top navigation bar
- Logo, breadcrumbs, search, user menu
- Persistent across all pages

**Sidebar.tsx**
- Organizer sidebar navigation
- 8 nav items (Dashboard, Tournaments, Matches, Scheduling, Results, Staff, Analytics, Help)
- Badge indicators (e.g., "3 pending in Scheduling")
- Responsive (hidden on mobile, visible on desktop)

**UserMenu.tsx**
- Dropdown menu triggered by user avatar
- 5 menu items (Profile, Settings, My Tournaments, Help, Sign Out)
- Click-outside close, escape key close
- ARIA menu role for accessibility

#### 2. UI Components (Primitives)

**Card.tsx**
- Container component with variants (default, flat, bordered, hoverable)
- Compound components: `Card.Header`, `Card.Title`, `Card.Content`, `Card.Footer`
- Padding sizes: none, sm, md, lg

**Example:**
```tsx
<Card variant="bordered" padding="md">
  <Card.Header>
    <Card.Title>Tournament Name</Card.Title>
  </Card.Header>
  <Card.Content>
    Details here...
  </Card.Content>
  <Card.Footer>
    <Button>View Details</Button>
  </Card.Footer>
</Card>
```

**Button.tsx**
- 5 variants (primary, secondary, danger, success, ghost)
- 3 sizes (sm, md, lg)
- Loading state with spinner
- `fullWidth` option

**Input.tsx**
- Form input with label, error, helpText
- Left/right icon support
- Required indicator
- ARIA error/help text linking

**Select.tsx**
- Dropdown select with label, error
- Options array support
- Chevron icon
- Placeholder support

**Modal.tsx**
- Accessible dialog with focus trap
- Escape key close, backdrop click close
- 4 sizes (sm, md, lg, xl)
- `Modal.Footer` compound component
- Body scroll lock when open

**Tabs.tsx**
- Tab navigation with keyboard support (arrow keys)
- `aria-selected` for active tab
- Disabled tab support

**Badge.tsx**
- 6 variants (default, primary, success, warning, error, info)
- 3 sizes (sm, md, lg)

**Table.tsx**
- Sortable data table
- Custom cell renderers
- `onRowClick` callback
- Empty state support

**EmptyState.tsx**
- Placeholder for empty lists
- Icon, title, description, optional CTA button

#### 3. Data Components (Domain-Specific)

**StatCard.tsx**
- Dashboard statistic display
- Value, label, trend indicator (up/down with %)
- Icon support
- 5 variants (default, primary, success, warning, error)

**LeaderboardTable.tsx**
- Tournament leaderboard display
- Rank badges (🥇🥈🥉 for top 3)
- Player avatars, W-L record
- Advancement status (advance, eliminate, undecided)

**MatchCard.tsx**
- Match display with 2 participants
- Scores, status badge (scheduled, in-progress, completed, disputed)
- Winner highlighting
- VS separator, scheduled time

**TournamentCard.tsx**
- Tournament card for listings
- Game icon header with gradient
- Status badge, prize pool badge
- Participant count, registration deadline
- Format, dates, CTA button

---

## Providers Directory (`providers/`)

### Purpose
Contains **React Context providers** for global application state (theme, auth, queries, toasts).

### Providers

#### `ThemeProvider.tsx` (Epic 9.4)
**Purpose:** Dark/light mode management with `next-themes`.

**Features:**
- System theme detection
- Persistent theme preference (localStorage)
- Theme toggle function
- No flash on page load

**Usage:**
```tsx
import { useTheme } from '@/providers/ThemeProvider';

function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  return <Button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>Toggle</Button>;
}
```

#### `AuthProvider.tsx` (Epic 9.4)
**Purpose:** Authentication state management (user, login, logout).

**Features:**
- Current user state
- `login(credentials)` function
- `logout()` function
- Token storage (cookies or localStorage)
- Protected route support

**Usage:**
```tsx
import { useAuth } from '@/providers/AuthProvider';

function UserProfile() {
  const { user, logout } = useAuth();
  if (!user) return <Login />;
  return <div>{user.name} <Button onClick={logout}>Sign Out</Button></div>;
}
```

#### `QueryProvider.tsx` (Epic 9.4)
**Purpose:** React Query (TanStack Query) configuration.

**Features:**
- Optimized defaults (5min staleTime, 3 retries)
- Global error handling
- Dev tools in development
- SSR-safe hydration

**Usage:**
```tsx
import { useQuery } from '@tanstack/react-query';

function TournamentList() {
  const { data, isLoading } = useQuery({
    queryKey: ['tournaments'],
    queryFn: () => client.tournaments.list(),
  });
  
  if (isLoading) return <Loading />;
  return <TournamentGrid tournaments={data} />;
}
```

#### `ToastProvider.tsx` (Epic 9.4)
**Purpose:** Global notification system (success, error, info, warning).

**Features:**
- Toast queue management
- Auto-dismiss (configurable duration)
- 4 variants (success, error, info, warning)
- Accessibility (ARIA live regions)

**Usage:**
```tsx
import { useToast } from '@/providers/ToastProvider';

function CreateTournamentForm() {
  const { showToast } = useToast();
  
  const handleSubmit = async () => {
    try {
      await client.tournaments.create(data);
      showToast({ message: 'Tournament created!', variant: 'success' });
    } catch (error) {
      showToast({ message: 'Failed to create tournament', variant: 'error' });
    }
  };
}
```

---

## Hooks Directory (`hooks/`)

### Purpose
Contains **custom React hooks** for reusable stateful logic.

### Hooks

#### `useDebounce.ts`
**Purpose:** Delay value updates (useful for search inputs).

**Usage:**
```tsx
import { useDebounce } from '@/hooks/useDebounce';

function SearchBar() {
  const [searchQuery, setSearchQuery] = useState('');
  const debouncedQuery = useDebounce(searchQuery, 500); // 500ms delay
  
  useEffect(() => {
    // Only triggers after 500ms of no typing
    fetchResults(debouncedQuery);
  }, [debouncedQuery]);
  
  return <Input value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />;
}
```

#### `useLocalStorage.ts`
**Purpose:** Sync React state with localStorage (SSR-safe).

**Usage:**
```tsx
import { useLocalStorage } from '@/hooks/useLocalStorage';

function TournamentFilters() {
  const [filters, setFilters] = useLocalStorage('tournament-filters', { status: 'all' });
  
  return (
    <Select 
      value={filters.status} 
      onChange={(status) => setFilters({ ...filters, status })}
    />
  );
}
```

#### `useMediaQuery.ts`
**Purpose:** Responsive breakpoint detection.

**Usage:**
```tsx
import { useIsMobile, useIsDesktop } from '@/hooks/useMediaQuery';

function ResponsiveLayout() {
  const isMobile = useIsMobile();
  const isDesktop = useIsDesktop();
  
  return (
    <div>
      {isMobile && <MobileNav />}
      {isDesktop && <Sidebar />}
    </div>
  );
}
```

---

## Library Directory (`lib/`)

### Purpose
Contains **utility functions** and **helper libraries** (formatting, API client, classnames).

### Files

#### `cn.ts`
**Purpose:** Conditional classname utility (combines multiple class strings).

**Implementation:**
```typescript
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

**Usage:**
```tsx
<div className={cn(
  'base-class',
  isActive && 'active-class',
  error && 'error-class',
  customClassName
)}>
  Content
</div>
```

#### `formatters.ts`
**Purpose:** Date, currency, number, and string formatting utilities.

**Functions:**
- `formatDate(date, format)` — Format dates (short, long, time)
- `formatCurrency(amount, currency)` — Format money ($1,234.56)
- `formatNumber(value)` — Format numbers with commas (1,234,567)
- `formatRelativeTime(date)` — Relative time ("5 minutes ago")
- `truncate(text, maxLength)` — Truncate long strings

**Usage:**
```tsx
import { formatDate, formatCurrency } from '@/lib/formatters';

<p>Tournament starts: {formatDate(tournament.start_date, 'long')}</p>
<p>Prize pool: {formatCurrency(tournament.prize_pool, 'USD')}</p>
```

#### `api.ts`
**Purpose:** DeltaCrown SDK wrapper (Epic 9.2 integration point).

**Current State:** Placeholder with usage documentation.

**Future Implementation:**
```typescript
import { DeltaCrownClient } from '@deltacrown/sdk';

export function getApiClient() {
  return new DeltaCrownClient({
    baseUrl: process.env.NEXT_PUBLIC_API_URL,
    // Auth token injection will be added
  });
}

export const client = getApiClient();
```

**Usage in Pages:**
```tsx
import { client } from '@/lib/api';

const tournaments = await client.tournaments.list();
```

---

## Styles Directory (`styles/`)

### Purpose
Contains **global CSS styles** with design token integration.

### Files

#### `globals.css` (Epic 9.4)
**Purpose:** Global CSS reset, design token CSS variables, base styles.

**Key Sections:**
1. **CSS Variables** — Design tokens as CSS custom properties
2. **Tailwind Directives** — `@tailwind base/components/utilities`
3. **Global Resets** — Box-sizing, margins, focus styles
4. **Typography** — Base font sizes, line heights
5. **Accessibility** — `.sr-only` class, focus-visible styles

**Example:**
```css
:root {
  /* Design tokens from design-tokens.json */
  --color-primary-500: #3B82F6;
  --color-success-500: #10B981;
  --spacing-4: 1rem;
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

@tailwind base;
@tailwind components;
@tailwind utilities;

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: var(--font-sans);
  background-color: var(--color-background);
  color: var(--color-text-primary);
}
```

**Usage:** Automatically imported in `app/layout.tsx`.

---

## Frontend SDK (`frontend_sdk/`)

### Purpose
TypeScript SDK from **Epic 9.2** for type-safe API consumption.

### Location
```
frontend_sdk/  (separate package, not in Frontend/ folder)
```

### Structure
```
frontend_sdk/
├── package.json              # Package metadata
├── tsconfig.json             # TypeScript config (strict mode)
├── README.md                 # SDK documentation
│
├── src/
│   ├── types/
│   │   ├── generated/        # Auto-generated from OpenAPI
│   │   │   ├── tournaments.ts
│   │   │   ├── matches.ts
│   │   │   └── ... (78 types)
│   │   └── curated/          # Hand-crafted domain types
│   │       ├── registration.ts
│   │       ├── stats.ts
│   │       └── ... (40 types)
│   │
│   ├── client/
│   │   └── DeltaCrownClient.ts  # Main SDK class (35 methods)
│   │
│   └── endpoints/
│       └── endpoints.ts       # Endpoint path configuration
│
└── tests/
    └── validation.test.ts     # Type validation tests
```

### Usage
See **[SDK_USAGE_GUIDE.md](./SDK_USAGE_GUIDE.md)** for detailed examples.

---

## Documentation (`Frontend/` and `DeveloperGuide/`)

### Purpose
Comprehensive developer documentation created in **Epic 9.5**.

### Structure
```
Documents/Modify_TournamentApp/Frontend/
├── design-tokens.json                     # Epic 9.3
├── tailwind.config.js                     # Epic 9.3
├── COMPONENT_LIBRARY.md                   # Epic 9.3
├── UI_PATTERNS.md                         # Epic 9.3
├── ACCESSIBILITY_GUIDELINES.md            # Epic 9.3
├── RESPONSIVE_DESIGN_GUIDE.md             # Epic 9.3
├── PHASE9_EPIC93_COMPLETION_SUMMARY.md    # Epic 9.3
├── PHASE9_EPIC94_COMPLETION_SUMMARY.md    # Epic 9.4
│
└── DeveloperGuide/                        # Epic 9.5
    ├── INTRODUCTION.md
    ├── PROJECT_STRUCTURE.md               # This file
    ├── SDK_USAGE_GUIDE.md
    ├── COMPONENTS_GUIDE.md
    ├── API_REFERENCE.md
    ├── WORKFLOW_GUIDE.md
    ├── LOCAL_SETUP.md
    ├── TROUBLESHOOTING.md
    ├── GLOSSARY.md
    ├── SECURITY_BEST_PRACTICES.md
    ├── CONTRIBUTING.md
    └── PHASE9_EPIC95_COMPLETION_SUMMARY.md
```

---

## File Naming Conventions

### General Rules

| File Type | Convention | Example |
|-----------|------------|---------|
| React Components | PascalCase | `TournamentCard.tsx` |
| Utility Functions | camelCase | `formatters.ts` |
| Hooks | camelCase with `use` prefix | `useDebounce.ts` |
| Constants | UPPER_SNAKE_CASE | `API_ENDPOINTS.ts` |
| Types/Interfaces | PascalCase | `TournamentDTO.ts` |
| Pages (App Router) | lowercase | `page.tsx`, `layout.tsx` |
| Config Files | kebab-case | `tailwind.config.js` |

### Component Naming

**Single Component per File:**
```
components/TournamentCard.tsx  →  export default function TournamentCard() {}
```

**Compound Components:**
```tsx
// Card.tsx
export function Card() {}
Card.Header = function CardHeader() {}
Card.Title = function CardTitle() {}
Card.Content = function CardContent() {}
Card.Footer = function CardFooter() {}
```

**Usage:**
```tsx
import { Card } from '@/components/Card';

<Card>
  <Card.Header>
    <Card.Title>Title</Card.Title>
  </Card.Header>
  <Card.Content>Content</Card.Content>
</Card>
```

### Import Aliases

**Configuration (`tsconfig.json`):**
```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

**Usage:**
```tsx
// ✅ Good — Absolute imports
import { Button } from '@/components/Button';
import { useAuth } from '@/providers/AuthProvider';
import { formatDate } from '@/lib/formatters';

// ❌ Bad — Relative imports
import { Button } from '../../../components/Button';
```

---

## Best Practices

### 1. Component Organization

**Keep components focused:**
- Each component should have a single responsibility
- Extract complex logic into custom hooks
- Use compound components for related UI elements (e.g., `Card.Header`, `Card.Footer`)

**Example:**
```tsx
// ✅ Good — Focused component
function TournamentCard({ tournament }: Props) {
  return <Card>...</Card>;
}

// ❌ Bad — Too many responsibilities
function TournamentDashboard() {
  // Fetching data, filtering, sorting, rendering...
}
```

### 2. Server vs Client Components

**Default to Server Components** (no `'use client'`):
```tsx
// app/tournaments/page.tsx (Server Component)
export default async function TournamentsPage() {
  const tournaments = await client.tournaments.list(); // Fetched on server
  return <TournamentGrid tournaments={tournaments} />;
}
```

**Use Client Components for interactivity** (`'use client'` directive):
```tsx
// components/TournamentGrid.tsx (Client Component)
'use client';

export function TournamentGrid({ tournaments }: Props) {
  const [filter, setFilter] = useState('all');
  // Client-side state, event handlers
  return <div>...</div>;
}
```

### 3. Type Safety

**Always define prop types:**
```tsx
// ✅ Good
interface TournamentCardProps {
  tournament: TournamentDTO;
  onClick?: () => void;
}

function TournamentCard({ tournament, onClick }: TournamentCardProps) {
  return <div>...</div>;
}

// ❌ Bad — No types
function TournamentCard({ tournament, onClick }) {
  return <div>...</div>;
}
```

### 4. Data Fetching

**Use React Query for client-side fetching:**
```tsx
import { useQuery } from '@tanstack/react-query';

const { data, isLoading, error } = useQuery({
  queryKey: ['tournaments', { status: 'open' }],
  queryFn: () => client.tournaments.list({ status: 'open' }),
});
```

**Use Server Components for initial page loads:**
```tsx
export default async function TournamentPage({ params }: { params: { id: string } }) {
  const tournament = await client.tournaments.get(params.id);
  return <TournamentDetail tournament={tournament} />;
}
```

---

## Do's and Don'ts

| Do ✅ | Don't ❌ |
|-------|----------|
| Use design tokens from `design-tokens.json` | Hard-code colors/spacing (`bg-blue-600`, `p-4`) |
| Use DeltaCrown SDK for API calls | Use raw `fetch()` without types |
| Use absolute imports (`@/components/...`) | Use relative imports (`../../../components`) |
| Create Server Components by default | Add `'use client'` unnecessarily |
| Co-locate related components | Create deeply nested folder structures |
| Use compound components for related UI | Create monolithic components |
| Type all props and return values | Use `any` or skip TypeScript |
| Use React Query for server state | Use `useState` for API data |
| Follow WCAG 2.1 AA guidelines | Skip accessibility attributes |
| Use semantic HTML | Use `<div>` for everything |

### Adding New Features

**Adding a new page:**
```bash
# Create page file in app/
touch app/new-feature/page.tsx

# File structure:
app/new-feature/
├── page.tsx         # Main page component
├── layout.tsx       # (Optional) Custom layout
└── loading.tsx      # (Optional) Loading UI
```

**Adding a new component:**
```bash
# Create component in components/
touch components/NewComponent.tsx

# File structure:
components/
├── NewComponent.tsx  # Component definition
└── ...
```

**Adding a new hook:**
```bash
# Create hook in hooks/
touch hooks/useNewHook.ts

# Naming: Always prefix with "use"
```

**Adding a utility function:**
```bash
# Add to existing file or create new in lib/
touch lib/newUtility.ts
```

### File Size Guidelines

- **Components:** Keep under 300 lines (split into smaller components if larger)
- **Hooks:** Keep under 100 lines (extract complex logic to separate utilities)
- **Pages:** Keep under 200 lines (extract UI to components)
- **Utilities:** Keep under 150 lines per file (group related functions)

### When to Extract

**Extract to a new component when:**
- UI block is reused in multiple places
- Component exceeds 300 lines
- UI has complex state management

**Extract to a hook when:**
- Stateful logic is reused across components
- Side effects become complex (multiple `useEffect` calls)

**Extract to a utility when:**
- Pure function used in multiple places
- Complex calculation or transformation logic

---

## Quick Reference

### Creating a New Page

1. Create `app/new-route/page.tsx`
2. Define async component for Server Component
3. Fetch data using SDK
4. Return JSX with components

**Example:**
```tsx
// app/leaderboards/page.tsx
import { client } from '@/lib/api';
import { LeaderboardTable } from '@/components/LeaderboardTable';

export default async function LeaderboardsPage() {
  const leaderboard = await client.leaderboards.get({ type: 'global' });
  
  return (
    <div className="p-6">
      <h1 className="text-heading-2xl font-bold">Leaderboards</h1>
      <LeaderboardTable entries={leaderboard.entries} />
    </div>
  );
}
```

### Creating a New Component

1. Create `components/ComponentName.tsx`
2. Define props interface
3. Add TypeScript strict types
4. Use design tokens for styling
5. Add accessibility attributes

**Example:**
```tsx
// components/PlayerCard.tsx
interface PlayerCardProps {
  player: PlayerDTO;
  onClick?: () => void;
}

export function PlayerCard({ player, onClick }: PlayerCardProps) {
  return (
    <Card 
      variant="bordered" 
      className="cursor-pointer hover:shadow-lg transition-shadow"
      onClick={onClick}
    >
      <Card.Header>
        <img src={player.avatar_url} alt={player.name} className="w-12 h-12 rounded-full" />
        <Card.Title>{player.name}</Card.Title>
      </Card.Header>
      <Card.Content>
        <p className="text-text-secondary">Rank: {player.rank}</p>
      </Card.Content>
    </Card>
  );
}
```

---

**Next Steps:**
- See **[SDK_USAGE_GUIDE.md](./SDK_USAGE_GUIDE.md)** for API integration patterns
- See **[COMPONENTS_GUIDE.md](./COMPONENTS_GUIDE.md)** for component API reference
- See **[LOCAL_SETUP.md](./LOCAL_SETUP.md)** for development environment setup
