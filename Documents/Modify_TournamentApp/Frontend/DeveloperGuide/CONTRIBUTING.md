# Contributing to DeltaCrown Organizer Console

## Table of Contents

1. [Introduction](#introduction)
2. [Project Philosophy](#project-philosophy)
3. [How to Propose Changes](#how-to-propose-changes)
4. [Coding Standards](#coding-standards)
5. [Adding New API Endpoints](#adding-new-api-endpoints)
6. [Adding UI Components](#adding-ui-components)
7. [Testing Requirements](#testing-requirements)
8. [Code Review Process](#code-review-process)

---

## Introduction

Welcome to the DeltaCrown Organizer Console contributor guide! This document outlines the process and standards for contributing to the frontend codebase.

**Who should read this:**

- New team members onboarding to the project
- Developers proposing features or bug fixes
- Code reviewers ensuring consistency

**Goals:**

- Maintain high code quality and consistency
- Ensure accessibility and performance standards
- Facilitate smooth collaboration across the team

---

## Project Philosophy

DeltaCrown follows strict architectural principles to ensure scalability, maintainability, and developer productivity.

### 1. Strict TypeScript

**All code must be fully typed.** No `any` types except in rare, documented cases.

**✅ Good:**

```typescript
interface TournamentFormData {
  name: string;
  game: number;
  bracket_type: 'single_elimination' | 'double_elimination';
  max_participants: number;
}

function createTournament(data: TournamentFormData): Promise<Tournament> {
  return client.tournaments.create(data);
}
```

**❌ Bad:**

```typescript
// ❌ Avoid `any`
function createTournament(data: any) {
  return client.tournaments.create(data);
}
```

**Exceptions**: External libraries without types may require `any`, but wrap them:

```typescript
// Acceptable: Wrapping untyped library
import untypedLib from 'some-untyped-lib';

function safeFetch(url: string): Promise<Response> {
  return untypedLib.fetch(url) as Promise<Response>;
}
```

---

### 2. Design Tokens Only

**All colors, spacing, and typography must use design tokens.** No hard-coded values.

**✅ Good:**

```tsx
<div className="text-brand-primary bg-semantic-success p-6">
  Success message
</div>
```

**❌ Bad:**

```tsx
<div className="text-blue-500 bg-green-100 p-6">
  Success message
</div>
```

**Why?** Ensures consistency, enables theme switching, simplifies design updates.

---

### 3. Accessibility AA Compliance

**All UI must meet WCAG 2.1 AA standards.** This includes:

- **Keyboard navigation** (Tab, Enter, Escape, Arrows)
- **ARIA attributes** (labels, roles, descriptions)
- **Color contrast** (4.5:1 for normal text, 3:1 for large)
- **Touch targets** (44×44px minimum)

**Example:**

```tsx
<button
  onClick={handleDelete}
  aria-label="Delete tournament"
  className="p-2 focus:ring-2 focus:ring-brand-primary"
>
  <TrashIcon />
</button>
```

See [COMPONENTS_GUIDE.md#accessibility](./COMPONENTS_GUIDE.md#accessibility) for details.

---

### 4. DTO-Only Data Flows

**All data from the API must use DTOs** (Data Transfer Objects) defined in the SDK.

**✅ Good:**

```typescript
import { Tournament } from 'deltacrown-sdk';

const tournament: Tournament = await client.tournaments.get(id);
```

**❌ Bad:**

```typescript
// ❌ Don't create custom types that don't match DTOs
interface MyTournament {
  tournamentId: number; // Wrong field name
  tournamentName: string;
}
```

**Why?** Ensures type safety, prevents frontend-backend mismatches.

---

## How to Propose Changes

### Branch Naming Conventions

Use descriptive branch names following this pattern:

```
<type>/<ticket-id>-<short-description>
```

**Types:**

- `feature/` – New features
- `fix/` – Bug fixes
- `refactor/` – Code refactoring (no behavior change)
- `docs/` – Documentation updates
- `chore/` – Maintenance tasks (deps, config)

**Examples:**

```
feature/DCP-123-add-tournament-filters
fix/DCP-456-fix-leaderboard-sorting
refactor/DCP-789-extract-auth-hook
docs/DCP-101-update-api-reference
chore/DCP-202-upgrade-react-query
```

---

### Commit Message Guidelines

Follow **Conventional Commits** format:

```
<type>(<scope>): <subject>

<body (optional)>

<footer (optional)>
```

**Types:**

- `feat` – New feature
- `fix` – Bug fix
- `refactor` – Code refactoring
- `docs` – Documentation
- `test` – Add or update tests
- `chore` – Maintenance

**Examples:**

```
feat(tournaments): add filters for status and game

Adds dropdown filters to the tournaments list page.
Users can filter by status (draft, in_progress, completed)
and game (displays game list from API).

Closes DCP-123
```

```
fix(leaderboard): correct sorting by ELO rating

Previously sorted alphabetically instead of numerically.
Now uses proper number comparison.

Fixes DCP-456
```

**Rules:**

- **Subject**: Max 72 characters, present tense, lowercase
- **Body**: Explain **what** and **why** (not how)
- **Footer**: Reference ticket (`Closes DCP-123`, `Fixes DCP-456`)

---

### Pull Request Template

Use this template when creating a PR:

````markdown
## Description

Brief summary of changes (1-2 sentences).

## Ticket

Closes DCP-XXX

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactoring
- [ ] Documentation
- [ ] Chore

## Changes Made

- Added tournament filters (status, game)
- Updated TournamentsPage component
- Added tests for filter logic

## Testing

- [ ] Tested locally
- [ ] Unit tests added/updated
- [ ] Manual QA steps documented below

### Manual QA Steps

1. Navigate to `/tournaments`
2. Select "In Progress" from status filter
3. Verify only in-progress tournaments appear
4. Select "League of Legends" from game filter
5. Verify only LoL tournaments appear

## Screenshots (if applicable)

![Filter UI](link-to-screenshot)

## Checklist

- [ ] Code follows project style guidelines
- [ ] TypeScript strict mode passes
- [ ] Design tokens used (no hard-coded colors/spacing)
- [ ] Accessibility tested (keyboard nav, ARIA)
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No console errors
````

---

### Code Review Expectations

**All PRs require at least 1 approval** before merging.

**Reviewers check for:**

- ✅ TypeScript strict compliance
- ✅ Design token usage
- ✅ Accessibility (ARIA, keyboard nav)
- ✅ Component reuse (don't reinvent existing components)
- ✅ API integration via SDK (no direct fetch calls)
- ✅ Tests added for new logic
- ✅ No regressions (existing functionality unaffected)

**Review timeframe**: 1-2 business days.

**How to request review:**

1. Assign reviewers in GitHub
2. Post in team Slack/Discord with PR link
3. Address feedback promptly

---

## Coding Standards

### React & Next.js Guidelines

#### Server vs Client Components

**Default to Server Components** unless you need:

- Interactive state (`useState`, `useEffect`)
- Browser APIs (`window`, `localStorage`)
- Event handlers

**Server Component Example:**

```tsx
// app/tournaments/page.tsx (default: Server Component)
export default async function TournamentsPage() {
  const tournaments = await client.tournaments.list();
  return (
    <div>
      {tournaments.map(t => <TournamentCard key={t.id} {...t} />)}
    </div>
  );
}
```

**Client Component Example:**

```tsx
// components/CreateTournamentModal.tsx
'use client';

export default function CreateTournamentModal() {
  const [isOpen, setIsOpen] = useState(false);
  const handleSubmit = async (data) => {
    await client.tournaments.create(data);
    setIsOpen(false);
  };

  return <Modal open={isOpen} onClose={() => setIsOpen(false)}>...</Modal>;
}
```

**Rule**: Use `'use client'` directive **only when necessary**.

---

#### Hooks Usage Rules

**✅ Do:**

- Use hooks at the **top level** of components (not in loops/conditions)
- Extract reusable logic into custom hooks
- Use React Query for data fetching

**✅ Custom Hook Example:**

```typescript
// hooks/useTournaments.ts
export function useTournaments(filters?: TournamentFilters) {
  return useQuery({
    queryKey: ['tournaments', filters],
    queryFn: () => client.tournaments.list(filters),
  });
}

// Usage
const { data: tournaments, isLoading } = useTournaments({ status: 'in_progress' });
```

**❌ Don't:**

```typescript
// ❌ BAD: Hook in condition
if (user) {
  const tournaments = useTournaments(); // Violates Rules of Hooks
}

// ✅ GOOD: Hook at top level
const tournaments = useTournaments();
if (!user) return null;
```

---

#### State Management Patterns

**Local state** (`useState`): Use for UI-only state (modals, forms).

**Server state** (React Query): Use for API data.

**Global state** (Context): Use sparingly for auth, theme, preferences.

**Example:**

```typescript
// Local state: Form inputs
const [name, setName] = useState('');

// Server state: API data
const { data: tournaments } = useQuery({
  queryKey: ['tournaments'],
  queryFn: client.tournaments.list,
});

// Global state: Auth context
const { user } = useAuth();
```

---

#### When to Create New Components vs Reuse

**Reuse existing components** whenever possible. Check [COMPONENTS_GUIDE.md](./COMPONENTS_GUIDE.md) first.

**Create new components when:**

- Existing components don't fit the use case
- Logic is repeated 3+ times
- Component exceeds 200 lines (split into smaller pieces)

**Example:**

```tsx
// ✅ GOOD: Reuse existing Card component
<Card>
  <Card.Header>
    <Card.Title>Tournament Details</Card.Title>
  </Card.Header>
  <Card.Content>...</Card.Content>
</Card>

// ❌ BAD: Creating a duplicate
function MyCard({ children }) {
  return <div className="bg-white rounded shadow p-4">{children}</div>;
}
```

---

### File Organization

**Component files:**

```
components/
  TournamentCard/
    TournamentCard.tsx       # Main component
    TournamentCard.test.tsx  # Tests
    index.ts                 # Re-export
```

**Hook files:**

```
hooks/
  useTournaments.ts
  useAuth.ts
```

**Utility files:**

```
lib/
  utils/
    formatDate.ts
    validators.ts
```

---

### Naming Conventions

| Type           | Convention         | Example                 |
| -------------- | ------------------ | ----------------------- |
| Components     | PascalCase         | `TournamentCard`        |
| Hooks          | camelCase (use...) | `useTournaments`        |
| Utilities      | camelCase          | `formatDate`            |
| Types          | PascalCase         | `Tournament`            |
| Constants      | UPPER_SNAKE_CASE   | `MAX_PARTICIPANTS`      |
| Files          | Match export name  | `TournamentCard.tsx`    |

---

## Adding New API Endpoints

When the backend adds a new endpoint, follow these steps:

### Step 1: Update SDK (Epic 9.2)

Add the endpoint to the SDK client.

**Example:**

```typescript
// frontend_sdk/src/client/TournamentsClient.ts
export class TournamentsClient {
  // Existing methods...

  // New endpoint
  async archive(tournamentId: number): Promise<void> {
    await this.request({
      method: 'POST',
      path: `/tournaments/v1/organizer/tournaments/${tournamentId}/archive/`,
    });
  }
}
```

**Add type (if needed):**

```typescript
// frontend_sdk/src/types/tournament.ts
export interface Tournament {
  // Existing fields...
  is_archived?: boolean; // New field
}
```

**Rebuild SDK:**

```powershell
cd frontend_sdk
pnpm build
```

---

### Step 2: Update API_REFERENCE.md

Document the new endpoint in [API_REFERENCE.md](./API_REFERENCE.md).

**Example:**

```markdown
### Archive Tournament

**`POST /api/tournaments/v1/organizer/tournaments/{id}/archive/`**

Archive a tournament (soft delete).

- **Auth**: 👔 Organizer (must own tournament)
- **Description**: Mark tournament as archived

**SDK Example:**

\`\`\`typescript
await client.tournaments.archive(tournamentId);
\`\`\`
```

---

### Step 3: Add Tests

Write unit tests for the SDK method.

**Example:**

```typescript
// frontend_sdk/tests/TournamentsClient.test.ts
describe('TournamentsClient', () => {
  it('should archive a tournament', async () => {
    const client = new TournamentsClient(mockConfig);
    await client.archive(123);
    
    expect(mockRequest).toHaveBeenCalledWith({
      method: 'POST',
      path: '/tournaments/v1/organizer/tournaments/123/archive/',
    });
  });
});
```

---

### Step 4: Use in Frontend

Integrate the SDK method in the frontend.

**Example:**

```tsx
// app/tournaments/[id]/page.tsx
'use client';

export default function TournamentDetailPage({ params }) {
  const { id } = params;
  const { mutate: archive } = useMutation({
    mutationFn: () => client.tournaments.archive(Number(id)),
    onSuccess: () => {
      toast.success('Tournament archived');
      router.push('/tournaments');
    },
  });

  return (
    <div>
      <Button onClick={() => archive()}>Archive Tournament</Button>
    </div>
  );
}
```

---

## Adding UI Components

### Step 1: Follow Component Library

Review [COMPONENTS_GUIDE.md](./COMPONENTS_GUIDE.md) to ensure your component fits the design system.

**Checklist:**

- ✅ Uses design tokens (no hard-coded colors/spacing)
- ✅ Follows naming conventions (PascalCase)
- ✅ Includes TypeScript props interface
- ✅ Accessible (ARIA, keyboard nav)
- ✅ Responsive (works on mobile, tablet, desktop)

---

### Step 2: Component Template

Use this template for new components:

```tsx
// components/MyComponent/MyComponent.tsx
import React from 'react';

interface MyComponentProps {
  /** Primary content */
  children: React.ReactNode;
  /** Component variant */
  variant?: 'primary' | 'secondary';
  /** Optional click handler */
  onClick?: () => void;
}

export function MyComponent({
  children,
  variant = 'primary',
  onClick,
}: MyComponentProps) {
  const variantClasses = {
    primary: 'bg-brand-primary text-white',
    secondary: 'bg-neutral-100 text-neutral-900',
  };

  return (
    <div
      className={`p-4 rounded ${variantClasses[variant]}`}
      onClick={onClick}
    >
      {children}
    </div>
  );
}
```

---

### Step 3: Keep Styling Tokenized

**❌ Bad:**

```tsx
<div className="bg-blue-500 text-white p-4">
  Content
</div>
```

**✅ Good:**

```tsx
<div className="bg-brand-primary text-white p-6">
  Content
</div>
```

**Custom tokens** (if needed):

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        custom: {
          accent: '#FF6B6B',
        },
      },
    },
  },
};
```

---

### Step 4: Accessibility Checklist

Before submitting a component PR:

- [ ] **Keyboard navigable** (Tab, Enter, Escape work)
- [ ] **ARIA attributes** added (`aria-label`, `role`, etc.)
- [ ] **Color contrast** meets 4.5:1 (use [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/))
- [ ] **Touch targets** are 44×44px minimum
- [ ] **Focus visible** (`:focus` styles applied)

**Example:**

```tsx
<button
  onClick={handleClick}
  aria-label="Close modal"
  className="p-3 focus:ring-2 focus:ring-brand-primary"
>
  <XIcon />
</button>
```

---

## Testing Requirements

### Unit Testing Guidelines

**Framework**: Jest + React Testing Library

**What to test:**

- Component rendering
- User interactions (clicks, form inputs)
- API integration (mocked)
- Edge cases (empty states, errors)

**Example:**

```tsx
// components/TournamentCard/TournamentCard.test.tsx
import { render, screen } from '@testing-library/react';
import { TournamentCard } from './TournamentCard';

describe('TournamentCard', () => {
  it('renders tournament name', () => {
    render(<TournamentCard name="Summer Championship" status="in_progress" />);
    expect(screen.getByText('Summer Championship')).toBeInTheDocument();
  });

  it('displays correct status badge', () => {
    render(<TournamentCard name="Test" status="completed" />);
    expect(screen.getByText('Completed')).toHaveClass('bg-semantic-success');
  });
});
```

---

### Type Safety Tests

**Ensure strict TypeScript compliance:**

```powershell
pnpm tsc --noEmit
```

No errors should appear.

---

### Manual QA Steps

**Before submitting PR:**

1. Test in **Chrome, Firefox, Safari** (cross-browser)
2. Test on **mobile, tablet, desktop** (responsive)
3. Test with **keyboard only** (no mouse)
4. Test with **screen reader** (VoiceOver, NVDA)
5. Check **console** for errors/warnings

**Document QA steps in PR** (see [PR Template](#pull-request-template)).

---

## Code Review Process

### Review Checklist

**Code Quality:**

- [ ] TypeScript strict mode passes
- [ ] No `any` types (or documented exceptions)
- [ ] Design tokens used (no hard-coded values)
- [ ] No console.log statements (use proper logging)

**Functionality:**

- [ ] Feature works as expected
- [ ] No regressions (existing features unaffected)
- [ ] Error handling implemented
- [ ] Loading states handled

**Accessibility:**

- [ ] Keyboard navigable
- [ ] ARIA attributes present
- [ ] Color contrast acceptable
- [ ] Touch targets sized correctly

**Testing:**

- [ ] Unit tests added/updated
- [ ] Tests pass (`pnpm test`)
- [ ] Manual QA completed

**Documentation:**

- [ ] Code comments for complex logic
- [ ] API_REFERENCE.md updated (if new endpoint)
- [ ] COMPONENTS_GUIDE.md updated (if new component)

---

### Providing Feedback

**Be constructive and specific:**

**❌ Bad feedback:**

```
This doesn't work.
```

**✅ Good feedback:**

```
The filter doesn't update the URL query params. 
Suggestion: Use `router.push()` with query string when filter changes.
```

**Use GitHub's suggestion feature:**

```diff
- const status = 'in_progress';
+ const status = filters.status || 'in_progress';
```

---

### Addressing Feedback

**Respond to all comments:**

- **Agree**: Implement the change, mark comment as resolved
- **Disagree**: Explain reasoning, propose alternative
- **Clarify**: Ask questions if feedback is unclear

**Don't:** Silently ignore comments or mark as resolved without changes.

---

## Summary: Quick Contribution Guide

1. **Create branch**: `feature/DCP-123-add-filters`
2. **Make changes**: Follow coding standards
3. **Write tests**: Unit tests + manual QA
4. **Commit**: `feat(tournaments): add status filter`
5. **Open PR**: Use PR template
6. **Request review**: Assign reviewers
7. **Address feedback**: Respond to comments
8. **Merge**: Once approved (squash or merge commit)

---

## Additional Resources

- **Architecture**: [INTRODUCTION.md](./INTRODUCTION.md)
- **Project Structure**: [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)
- **SDK Guide**: [SDK_USAGE_GUIDE.md](./SDK_USAGE_GUIDE.md)
- **Component Library**: [COMPONENTS_GUIDE.md](./COMPONENTS_GUIDE.md)
- **API Reference**: [API_REFERENCE.md](./API_REFERENCE.md)

**Questions?** Ask in team Slack/Discord or open a GitHub Discussion.

---

**Thank you for contributing to DeltaCrown! 🚀**
