# PART 4.1: UI/UX Design Specifications - Foundations & Component Library

**Navigation:**  
← [Previous: PART_3.2_DATABASE_CONSTRAINTS_MIGRATION.md](PART_3.2_DATABASE_CONSTRAINTS_MIGRATION.md) | [Next: PART_4.2 (Tournament & Registration Screens - Coming Soon)](PART_4.2_TOURNAMENT_REGISTRATION_SCREENS.md) →

**Contents:** Introduction, Design Philosophy, Design System Foundation (Colors, Typography, Spacing, Shadows, Animation, Grid, Icons), Component Library (Buttons, Cards, Forms)

---

*This is Part 4.1 of the UI/UX Design Specifications (Lines 1-1401 from PROPOSAL_PART_4_UI_UX_DESIGN_SPECIFICATIONS.md)*

---

# Part 4: UI/UX Design Specifications

**DeltaCrown Tournament Engine**  
**Version:** 1.0  
**Date:** November 3, 2025  
**Author:** Design & Development Team

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Design Philosophy](#2-design-philosophy)
3. [Design System Foundation](#3-design-system-foundation)
4. [Component Library](#4-component-library)
5. [Tournament Management Screens](#5-tournament-management-screens)
6. [Registration & Payment Flow](#6-registration--payment-flow)
7. [Bracket & Match Screens](#7-bracket--match-screens)
8. [Player Experience Screens](#8-player-experience-screens)
9. [Spectator & Community Screens](#9-spectator--community-screens)
10. [Mobile Design Patterns](#10-mobile-design-patterns)
11. [Accessibility Guidelines](#11-accessibility-guidelines)
12. [Animation & Interaction Patterns](#12-animation--interaction-patterns)

---

## 1. Introduction

This document provides comprehensive UI/UX design specifications for the DeltaCrown Tournament Engine. It serves as the bridge between the technical architecture (Part 2) and the visual implementation, ensuring a consistent, accessible, and engaging user experience.

### Document Purpose

- **For Designers:** Design system, component specifications, screen layouts
- **For Frontend Developers:** Implementation guidelines, component structure, responsive behavior
- **For Stakeholders:** Visual representation of features and user flows
- **For QA:** Testing criteria for UI consistency and accessibility

### Design Goals

1. **Bangladesh-First:** Optimized for local context (mobile-first, data-efficient, BDT currency)
2. **Gaming Aesthetic:** Modern, energetic design that resonates with esports culture
3. **Performance:** Fast loading, smooth animations, efficient asset usage
4. **Accessibility:** WCAG 2.1 AA compliant, keyboard navigable, screen reader friendly
5. **Scalability:** Component-based system that grows with platform needs

### Target Devices & Browsers

**Primary Devices (80% traffic):**
- Mobile: 360x640 to 428x926 (iOS/Android)
- Tablet: 768x1024 to 1024x1366 (iPad, Android tablets)
- Desktop: 1366x768 to 1920x1080

**Browser Support:**
- Chrome 90+ (primary)
- Firefox 88+
- Safari 14+ (iOS/macOS)
- Edge 90+

---

## 2. Design Philosophy

### Core Principles

**1. Clarity Over Complexity**
- Information hierarchy guides user attention
- Single primary action per screen
- Progressive disclosure for advanced features
- Clear visual feedback for all interactions

**2. Speed & Efficiency**
- Minimize clicks to core actions
- Smart defaults reduce form fields
- Keyboard shortcuts for power users
- Optimistic UI updates

**3. Trust & Transparency**
- Clear payment verification process
- Real-time tournament status updates
- Transparent dispute resolution
- Organizer accountability (profiles, ratings)

**4. Community & Excitement**
- Live match updates create urgency
- Social features encourage engagement
- Achievements and badges gamify participation
- Sponsor visibility enhances professionalism

### Design Language

**Tone & Voice:**
- **Professional yet Energetic:** Serious about competition, exciting about esports
- **Inclusive & Welcoming:** Accessible to casual and hardcore gamers
- **Local & Global:** Bangladesh-first but internationally competitive

**Visual Style:**
- **Dark Mode Primary:** Reduces eye strain, aligns with gaming culture
- **Neon Accents:** High-contrast highlights for CTAs and status indicators
- **Clean Typography:** Legible at all sizes, professional hierarchy
- **Purposeful Animation:** Enhances understanding, never decorative only

### Tournament State Machine

**Purpose:** Visual alignment between backend state enums and UI transitions to guide animations, modal behavior, and conditional component rendering.

**State Flow Diagram:**

```
┌──────────┐
│  DRAFT   │ (Organizer only, hidden from public)
└────┬─────┘
     │ Publish Action
     ▼
┌──────────┐
│PUBLISHED │ (Public view, registration locked)
└────┬─────┘
     │ Open Registration Action
     ▼
┌───────────────┐
│ REGISTRATION  │ (Accept sign-ups, payment submissions)
│     OPEN      │ ← Most UI interactions happen here
└───────┬───────┘
        │ Auto-transition at start_time
        ▼
┌──────────┐
│ ONGOING  │ (Brackets locked, match results, live HUD)
└────┬─────┘
     │ Manual completion or auto after final match
     ▼
┌──────────┐
│COMPLETED │ (Winners declared, certificates issued)
└────┬─────┘
     │ Auto-transition after 90 days (configurable)
     ▼
┌──────────┐
│ ARCHIVED │ (Read-only, search excluded by default)
└──────────┘

  ┌──────────┐
  │CANCELLED │ (Can transition from any state)
  └──────────┘
```

**State-Specific UI Behaviors:**

| State | Public Visibility | Registration CTA | Bracket View | Match Submission | Certificate Access |
|-------|-------------------|------------------|--------------|------------------|--------------------|
| **Draft** | ❌ Organizer only | ❌ Hidden | ❌ Hidden | ❌ Disabled | ❌ Not issued |
| **Published** | ✅ Public view | 🔒 "Registration Opens [Date]" | 👁️ Preview (empty) | ❌ Disabled | ❌ Not issued |
| **Registration Open** | ✅ Public view | ✅ "Register Now" (primary) | 👁️ Preview (filling) | ❌ Disabled | ❌ Not issued |
| **Ongoing** | ✅ Public view | 🔒 "Registration Closed" | ✅ Live bracket | ✅ Enabled | ⏳ Pending completion |
| **Completed** | ✅ Public view | 🔒 "Tournament Ended" | ✅ Final standings | 🔒 Read-only | ✅ Issued to winners |
| **Archived** | 🔍 Search only | 🔒 "Archived" | ✅ Historical view | 🔒 Read-only | ✅ Still accessible |
| **Cancelled** | ⚠️ Public (with notice) | 🔒 "Cancelled" | ❌ Hidden | ❌ Disabled | ❌ Not issued |

**Transition Animations:**

1. **Published → Registration Open:**
   - Confetti animation on tournament page
   - "Register Now" button pulses (3 times)
   - Toast notification to followers: "Registration is now open!"
   - Email/SMS to interested users

2. **Registration Open → Ongoing:**
   - Countdown timer reaches 00:00:00
   - Auto-redirect participants to bracket view
   - Banner change: "🔴 LIVE" badge appears
   - Disable registration forms (fade out + disable)

3. **Ongoing → Completed:**
   - Final match result triggers completion modal
   - Winners podium animation (1st, 2nd, 3rd place)
   - Certificate generation background task
   - "View Certificate" CTA for winners

4. **Completed → Archived:**
   - No user-facing animation (background transition)
   - Search results exclude by default (can opt-in with filter)
   - Historical badge on tournament card

5. **Any State → Cancelled:**
   - Red banner: "⚠️ This tournament has been cancelled"
   - Refund notice (if entry fees collected)
   - Contact organizer CTA
   - Dim tournament card (grayscale filter)

**Backend Enum Alignment:**

Ensure these states match your Django model `TournamentStatus` choices:

```python
class TournamentStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    PUBLISHED = 'PUBLISHED', 'Published'
    REGISTRATION_OPEN = 'REGISTRATION_OPEN', 'Registration Open'
    ONGOING = 'ONGOING', 'Ongoing'
    COMPLETED = 'COMPLETED', 'Completed'
    ARCHIVED = 'ARCHIVED', 'Archived'
    CANCELLED = 'CANCELLED', 'Cancelled'
```

**Conditional Rendering Examples:**

```html
<!-- Show registration CTA only if state allows -->
{% if tournament.status == 'REGISTRATION_OPEN' %}
    <button class="btn-primary" data-analytics-id="dc-btn-register">
        Register Now
    </button>
{% elif tournament.status == 'PUBLISHED' %}
    <button class="btn-secondary" disabled>
        Registration Opens {{ tournament.registration_opens_at|date:"M d, g:i A" }}
    </button>
{% elif tournament.status == 'ONGOING' %}
    <span class="badge badge-live">🔴 LIVE</span>
{% endif %}

<!-- Bracket visibility -->
{% if tournament.status in ['ONGOING', 'COMPLETED', 'ARCHIVED'] %}
    <a href="{% url 'tournament_bracket' tournament.slug %}" 
       data-analytics-id="dc-link-bracket">
        View Bracket
    </a>
{% endif %}
```

**State Transition Validation:**

- Draft → Published: Requires all mandatory fields (date, format, teams)
- Published → Registration Open: Requires start_time set
- Registration Open → Ongoing: Auto-trigger at start_time (cron job)
- Ongoing → Completed: Requires all matches resolved OR manual override
- Any → Cancelled: Requires cancellation reason (logged in admin)

---

## 3. Design System Foundation

### 3.1 Color Palette

**Primary Colors (Dark Theme):**

```css
/* Background Layers */
--bg-primary: #0A0E1A;      /* Main background (deep navy) */
--bg-secondary: #151928;    /* Card backgrounds */
--bg-tertiary: #1F2937;     /* Elevated elements (modals, dropdowns) */
--bg-hover: #2D3748;        /* Hover states */

/* Brand Colors */
--brand-primary: #3B82F6;   /* DeltaCrown Blue (primary CTAs) */
--brand-secondary: #8B5CF6; /* Purple (secondary actions) */
--brand-accent: #F59E0B;    /* Amber (highlights, warnings) */

/* Semantic Colors */
--success: #10B981;         /* Green (confirmed, completed) */
--warning: #F59E0B;         /* Amber (pending, attention needed) */
--error: #EF4444;           /* Red (errors, disputes) */
--info: #3B82F6;            /* Blue (information, neutral) */

/* Neon Accents (Gaming Aesthetic) */
--neon-cyan: #06B6D4;       /* Live indicators */
--neon-magenta: #EC4899;    /* Featured tournaments */
--neon-lime: #84CC16;       /* Online status, check-in */

/* Text Colors */
--text-primary: #F9FAFB;    /* Primary text (white) */
--text-secondary: #9CA3AF;  /* Secondary text (gray) */
--text-tertiary: #6B7280;   /* Tertiary text (muted) */
--text-disabled: #4B5563;   /* Disabled text */

/* Borders & Dividers */
--border-primary: #374151;  /* Primary borders */
--border-secondary: #1F2937;/* Subtle dividers */
--border-accent: #3B82F6;   /* Highlighted borders */
```

**Light Theme (Optional):**

```css
/* Background Layers (Light) */
--bg-primary-light: #FFFFFF;
--bg-secondary-light: #F3F4F6;
--bg-tertiary-light: #E5E7EB;

/* Text Colors (Light) */
--text-primary-light: #111827;
--text-secondary-light: #4B5563;
--text-tertiary-light: #6B7280;
```

**Color Usage Guidelines:**

| Color | Use Case | Example |
|-------|----------|---------|
| `--brand-primary` | Primary CTAs, active states | "Register Now", active nav links |
| `--brand-secondary` | Secondary actions, badges | "View Details", achievement badges |
| `--brand-accent` | Highlights, featured items | Featured tournaments, new notifications |
| `--success` | Confirmations, completed states | Payment verified, match completed |
| `--warning` | Pending actions, attention | Payment pending, check-in required |
| `--error` | Errors, disputes, rejections | Payment rejected, dispute filed |
| `--neon-cyan` | Live/real-time indicators | Live match badge, streaming indicator |

**Alert & Message Color Tokens** (for consistent error/success/warning messaging):

| State | Text Color | Background | Border | Use Case |
|-------|-----------|------------|--------|----------|
| **Success** | `--success` (#10B981) | `#ECFDF5` (green-50) | `#10B981` | Payment approved, registration confirmed |
| **Warning** | `--warning` (#F59E0B) | `#FFFBEB` (amber-50) | `#F59E0B` | Payment pending, deadline approaching |
| **Error** | `--error` (#EF4444) | `#FEF2F2` (red-50) | `#EF4444` | Payment rejected, validation failed |
| **Info** | `--info` (#3B82F6) | `#EFF6FF` (blue-50) | `#3B82F6` | Helpful tips, neutral information |

**Alert Component CSS:**

```css
/* Base Alert Styles */
.alert {
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid;
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
}

/* Success Alert */
.alert-success {
    background-color: #ECFDF5;
    border-color: var(--success);
    color: #065F46; /* green-800 for readability */
}

/* Warning Alert */
.alert-warning {
    background-color: #FFFBEB;
    border-color: var(--warning);
    color: #92400E; /* amber-800 */
}

/* Error Alert */
.alert-error {
    background-color: #FEF2F2;
    border-color: var(--error);
    color: #991B1B; /* red-800 */
}

/* Info Alert */
.alert-info {
    background-color: #EFF6FF;
    border-color: var(--info);
    color: #1E40AF; /* blue-800 */
}
```

---

### 3.2 Typography

**Font Stack:**

```css
/* Primary Font (UI) */
--font-primary: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;

/* Secondary Font (Headings) */
--font-heading: 'Outfit', 'Inter', sans-serif;

/* Monospace Font (Codes, IDs) */
--font-mono: 'Fira Code', 'Courier New', monospace;

/* Bengali Support */
--font-bengali: 'Noto Sans Bengali', sans-serif;
```

**Type Scale:**

```css
/* Font Sizes */
--text-xs: 0.75rem;    /* 12px - Captions, meta info */
--text-sm: 0.875rem;   /* 14px - Body small, labels */
--text-base: 1rem;     /* 16px - Body text */
--text-lg: 1.125rem;   /* 18px - Emphasized text */
--text-xl: 1.25rem;    /* 20px - Subheadings */
--text-2xl: 1.5rem;    /* 24px - Section headings */
--text-3xl: 1.875rem;  /* 30px - Page headings */
--text-4xl: 2.25rem;   /* 36px - Hero text */
--text-5xl: 3rem;      /* 48px - Display text */

/* Font Weights */
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
--font-black: 900;

/* Line Heights */
--leading-tight: 1.25;   /* Headings */
--leading-normal: 1.5;   /* Body text */
--leading-relaxed: 1.75; /* Long-form content */
```

**Typography Hierarchy:**

```html
<!-- H1 - Page Title -->
<h1 class="text-4xl font-bold text-primary leading-tight">
    DeltaCrown Valorant Cup 2025
</h1>

<!-- H2 - Section Heading -->
<h2 class="text-3xl font-semibold text-primary leading-tight">
    Tournament Details
</h2>

<!-- H3 - Subsection Heading -->
<h3 class="text-2xl font-semibold text-primary">
    Registration Information
</h3>

<!-- H4 - Card Heading -->
<h4 class="text-xl font-medium text-primary">
    Participant List
</h4>

<!-- Body Text -->
<p class="text-base text-secondary leading-normal">
    This tournament follows FACEIT anti-cheat rules...
</p>

<!-- Small Text / Caption -->
<span class="text-sm text-tertiary">
    Created on November 3, 2025
</span>

<!-- Meta / Micro Text -->
<span class="text-xs text-tertiary uppercase tracking-wide">
    VALORANT • 5V5 • SINGLE ELIMINATION
</span>
```

---

### 3.3 Spacing System

**Spacing Scale (Tailwind-based):**

```css
--space-0: 0;          /* 0px */
--space-1: 0.25rem;    /* 4px */
--space-2: 0.5rem;     /* 8px */
--space-3: 0.75rem;    /* 12px */
--space-4: 1rem;       /* 16px */
--space-5: 1.25rem;    /* 20px */
--space-6: 1.5rem;     /* 24px */
--space-8: 2rem;       /* 32px */
--space-10: 2.5rem;    /* 40px */
--space-12: 3rem;      /* 48px */
--space-16: 4rem;      /* 64px */
--space-20: 5rem;      /* 80px */
--space-24: 6rem;      /* 96px */
```

**Spacing Guidelines:**

| Element | Spacing | Example |
|---------|---------|---------|
| Component padding (small) | `space-4` (16px) | Button padding, input fields |
| Component padding (medium) | `space-6` (24px) | Card padding, modal padding |
| Component padding (large) | `space-8` (32px) | Section padding, hero padding |
| Element gap (tight) | `space-2` (8px) | Icon + text, form field gap |
| Element gap (normal) | `space-4` (16px) | Button group, list items |
| Element gap (loose) | `space-6` (24px) | Card grid, section dividers |
| Section spacing | `space-12` (48px) | Between major sections |
| Page margins (mobile) | `space-4` (16px) | Left/right container padding |
| Page margins (desktop) | `space-8` (32px) | Left/right container padding |

---

### 3.4 Border Radius

```css
--radius-none: 0;
--radius-sm: 0.25rem;   /* 4px - Small elements */
--radius-base: 0.5rem;  /* 8px - Buttons, inputs */
--radius-lg: 0.75rem;   /* 12px - Cards */
--radius-xl: 1rem;      /* 16px - Modals, large cards */
--radius-2xl: 1.5rem;   /* 24px - Hero sections */
--radius-full: 9999px;  /* Circular elements */
```

---

### 3.5 Shadows & Elevation

```css
/* Shadow Levels */
--shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.3);
--shadow-base: 0 1px 3px 0 rgba(0, 0, 0, 0.4), 0 1px 2px 0 rgba(0, 0, 0, 0.3);
--shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -1px rgba(0, 0, 0, 0.3);
--shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -2px rgba(0, 0, 0, 0.3);
--shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.3);
--shadow-2xl: 0 25px 50px -12px rgba(0, 0, 0, 0.6);

/* Glow Effects (Gaming Aesthetic) */
--glow-primary: 0 0 20px rgba(59, 130, 246, 0.5);    /* Blue glow */
--glow-success: 0 0 20px rgba(16, 185, 129, 0.5);    /* Green glow */
--glow-warning: 0 0 20px rgba(245, 158, 11, 0.5);    /* Amber glow */
--glow-live: 0 0 30px rgba(6, 182, 212, 0.7);        /* Cyan glow for live */
```

**Elevation Hierarchy:**

| Level | Shadow | Use Case |
|-------|--------|----------|
| 0 | None | Flat elements, text |
| 1 | `shadow-sm` | Subtle cards, list items |
| 2 | `shadow-base` | Default cards, inputs |
| 3 | `shadow-md` | Elevated cards, dropdowns |
| 4 | `shadow-lg` | Modals, popovers |
| 5 | `shadow-xl` | Mega menus, full overlays |
| Special | `glow-*` | Live indicators, CTAs, featured items |

---

### 3.6 Animation Timing

```css
/* Duration */
--duration-fast: 150ms;      /* Instant feedback (hover, focus) */
--duration-base: 250ms;      /* Standard transitions */
--duration-slow: 350ms;      /* Complex animations */
--duration-slower: 500ms;    /* Page transitions, modals */

/* Easing Functions */
--ease-in: cubic-bezier(0.4, 0, 1, 1);
--ease-out: cubic-bezier(0, 0, 0.2, 1);
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
--ease-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55);

/* Standard Transition */
--transition-base: all var(--duration-base) var(--ease-out);
```

---

### 3.7 Responsive Breakpoints

```css
/* Mobile First Approach */
--screen-sm: 640px;   /* Small devices (landscape phones) */
--screen-md: 768px;   /* Medium devices (tablets) */
--screen-lg: 1024px;  /* Large devices (laptops) */
--screen-xl: 1280px;  /* Extra large (desktops) */
--screen-2xl: 1536px; /* 2X large (large desktops) */
```

**Breakpoint Usage:**

```css
/* Mobile (default) */
.container {
    padding: var(--space-4);
}

/* Tablet and up */
@media (min-width: 768px) {
    .container {
        padding: var(--space-8);
        max-width: 720px;
        margin: 0 auto;
    }
}

/* Desktop and up */
@media (min-width: 1024px) {
    .container {
        max-width: 960px;
    }
}
```

---

### 3.8 Grid System

**12-Column Grid:**

```css
.grid-container {
    display: grid;
    grid-template-columns: repeat(12, 1fr);
    gap: var(--space-6);
}

/* Column Spans */
.col-span-1 { grid-column: span 1; }
.col-span-2 { grid-column: span 2; }
.col-span-3 { grid-column: span 3; }
.col-span-4 { grid-column: span 4; }
.col-span-6 { grid-column: span 6; }
.col-span-8 { grid-column: span 8; }
.col-span-12 { grid-column: span 12; }
```

**Common Layouts:**

```html
<!-- Two-column layout (sidebar + content) -->
<div class="grid grid-cols-12 gap-6">
    <aside class="col-span-12 lg:col-span-3"><!-- Sidebar --></aside>
    <main class="col-span-12 lg:col-span-9"><!-- Content --></main>
</div>

<!-- Three-column card grid -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
    <div class="card"><!-- Card 1 --></div>
    <div class="card"><!-- Card 2 --></div>
    <div class="card"><!-- Card 3 --></div>
</div>

<!-- Four-column stats -->
<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
    <div class="stat"><!-- Stat 1 --></div>
    <div class="stat"><!-- Stat 2 --></div>
    <div class="stat"><!-- Stat 3 --></div>
    <div class="stat"><!-- Stat 4 --></div>
</div>
```

---

### 3.9 Iconography

**Icon Library:** Heroicons (by Tailwind Labs)

**Icon Sizes:**

```css
--icon-xs: 16px;   /* Inline with text */
--icon-sm: 20px;   /* Small icons, badges */
--icon-base: 24px; /* Default icon size */
--icon-lg: 32px;   /* Large icons, features */
--icon-xl: 48px;   /* Hero icons, empty states */
```

**Icon Usage Guidelines:**
- Always include text labels for accessibility
- Use outline style for inactive/secondary actions
- Use solid style for active/primary actions
- Maintain consistent stroke width (2px default)
- Color should match adjacent text color

**Common Icons:**

| Context | Icon | Heroicon Name |
|---------|------|---------------|
| Tournament | 🏆 | `TrophyIcon` |
| Registration | ✅ | `CheckCircleIcon` |
| Payment | 💳 | `CreditCardIcon` |
| Match | ⚔️ | `FireIcon` |
| Live | 🔴 | `SignalIcon` |
| Teams | 👥 | `UsersIcon` |
| Schedule | 📅 | `CalendarIcon` |
| Settings | ⚙️ | `CogIcon` |
| Notifications | 🔔 | `BellIcon` |
| Chat | 💬 | `ChatBubbleIcon` |

---

## 4. Component Library

### 4.1 Buttons

**Button Variants:**

```html
<!-- Primary Button (Main CTAs) -->
<button class="btn btn-primary">
    <span class="btn-icon">
        <svg><!-- Icon --></svg>
    </span>
    <span class="btn-text">Register Now</span>
</button>

<!-- Secondary Button -->
<button class="btn btn-secondary">
    View Details
</button>

<!-- Ghost Button (Subtle Actions) -->
<button class="btn btn-ghost">
    Cancel
</button>

<!-- Danger Button (Destructive Actions) -->
<button class="btn btn-danger">
    Delete Tournament
</button>

<!-- Disabled Button -->
<button class="btn btn-primary" disabled>
    Registration Closed
</button>

<!-- Loading Button -->
<button class="btn btn-primary btn-loading">
    <span class="spinner"></span>
    Processing...
</button>
```

**Button Styles:**

```css
.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-2);
    padding: var(--space-3) var(--space-6);
    font-size: var(--text-base);
    font-weight: var(--font-medium);
    line-height: 1;
    border-radius: var(--radius-base);
    border: 2px solid transparent;
    cursor: pointer;
    transition: var(--transition-base);
    white-space: nowrap;
}

/* Primary Button */
.btn-primary {
    background: var(--brand-primary);
    color: var(--text-primary);
    box-shadow: var(--glow-primary);
}

.btn-primary:hover {
    background: #2563EB;
    transform: translateY(-1px);
    box-shadow: var(--shadow-md), var(--glow-primary);
}

.btn-primary:active {
    transform: translateY(0);
}

/* Secondary Button */
.btn-secondary {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border-color: var(--border-primary);
}

.btn-secondary:hover {
    background: var(--bg-hover);
    border-color: var(--brand-primary);
}

/* Ghost Button */
.btn-ghost {
    background: transparent;
    color: var(--text-secondary);
}

.btn-ghost:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
}

/* Danger Button */
.btn-danger {
    background: var(--error);
    color: var(--text-primary);
}

.btn-danger:hover {
    background: #DC2626;
}

/* Disabled State */
.btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    pointer-events: none;
}

/* Loading State */
.btn-loading {
    pointer-events: none;
}

.btn-loading .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}
```

**Button Sizes:**

```html
<!-- Small -->
<button class="btn btn-primary btn-sm">Small</button>

<!-- Base (default) -->
<button class="btn btn-primary">Base</button>

<!-- Large -->
<button class="btn btn-primary btn-lg">Large</button>
```

```css
.btn-sm {
    padding: var(--space-2) var(--space-4);
    font-size: var(--text-sm);
}

.btn-lg {
    padding: var(--space-4) var(--space-8);
    font-size: var(--text-lg);
}
```

---

### 4.2 Card Components

**Tournament Card:**

```html
<article class="card card-tournament">
    <!-- Card Header with Image -->
    <div class="card-image">
        <img src="tournament-banner.jpg" alt="Valorant Cup 2025">
        <div class="card-badge card-badge-live">
            <span class="badge-dot"></span>
            LIVE
        </div>
    </div>
    
    <!-- Card Body -->
    <div class="card-body">
        <div class="card-meta">
            <span class="badge badge-game">VALORANT</span>
            <span class="card-date">
                <svg class="icon-sm"><!-- Calendar icon --></svg>
                Dec 15, 2025
            </span>
        </div>
        
        <h3 class="card-title">DeltaCrown Valorant Cup 2025</h3>
        
        <div class="card-stats">
            <div class="stat">
                <span class="stat-value">32</span>
                <span class="stat-label">Teams</span>
            </div>
            <div class="stat">
                <span class="stat-value">৳50,000</span>
                <span class="stat-label">Prize Pool</span>
            </div>
            <div class="stat">
                <span class="stat-value">16/32</span>
                <span class="stat-label">Registered</span>
            </div>
        </div>
        
        <div class="card-footer">
            <button class="btn btn-primary btn-sm">Register Now</button>
            <button class="btn btn-ghost btn-sm">View Details</button>
        </div>
    </div>
</article>
```

**Card Styles:**

```css
.card {
    background: var(--bg-secondary);
    border-radius: var(--radius-lg);
    overflow: hidden;
    border: 1px solid var(--border-secondary);
    transition: var(--transition-base);
}

.card:hover {
    border-color: var(--border-accent);
    box-shadow: var(--shadow-lg);
    transform: translateY(-4px);
}

.card-image {
    position: relative;
    aspect-ratio: 16/9;
    overflow: hidden;
}

.card-image img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: var(--transition-base);
}

.card:hover .card-image img {
    transform: scale(1.05);
}

.card-badge {
    position: absolute;
    top: var(--space-3);
    right: var(--space-3);
    padding: var(--space-2) var(--space-3);
    background: rgba(0, 0, 0, 0.8);
    backdrop-filter: blur(8px);
    border-radius: var(--radius-base);
    font-size: var(--text-xs);
    font-weight: var(--font-bold);
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: var(--space-2);
}

.card-badge-live {
    background: rgba(6, 182, 212, 0.2);
    color: var(--neon-cyan);
    border: 1px solid var(--neon-cyan);
    box-shadow: var(--glow-live);
}

.badge-dot {
    width: 8px;
    height: 8px;
    background: var(--neon-cyan);
    border-radius: 50%;
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.card-body {
    padding: var(--space-6);
}

.card-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--space-4);
}

.card-date {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    color: var(--text-secondary);
    font-size: var(--text-sm);
}

.card-title {
    font-size: var(--text-xl);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    margin-bottom: var(--space-4);
    line-height: var(--leading-tight);
}

.card-stats {
    display: flex;
    gap: var(--space-6);
    padding: var(--space-4) 0;
    margin-bottom: var(--space-4);
    border-top: 1px solid var(--border-secondary);
    border-bottom: 1px solid var(--border-secondary);
}

.stat {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
}

.stat-value {
    font-size: var(--text-lg);
    font-weight: var(--font-bold);
    color: var(--brand-primary);
}

.stat-label {
    font-size: var(--text-xs);
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.card-footer {
    display: flex;
    gap: var(--space-3);
}
```

**Match Card:**

```html
<article class="card card-match">
    <div class="match-header">
        <span class="match-round">SEMIFINALS</span>
        <span class="match-status match-status-live">LIVE</span>
    </div>
    
    <div class="match-teams">
        <div class="team team-winner">
            <img src="team1-logo.png" alt="Team Alpha" class="team-logo">
            <span class="team-name">Team Alpha</span>
            <span class="team-score">13</span>
        </div>
        
        <div class="match-divider">
            <span class="match-vs">VS</span>
        </div>
        
        <div class="team">
            <img src="team2-logo.png" alt="Team Beta" class="team-logo">
            <span class="team-name">Team Beta</span>
            <span class="team-score">8</span>
        </div>
    </div>
    
    <div class="match-footer">
        <button class="btn btn-ghost btn-sm">
            <svg class="icon-sm"><!-- Eye icon --></svg>
            Watch Stream
        </button>
        <button class="btn btn-ghost btn-sm">
            View Details
        </button>
    </div>
</article>
```

**Match Card Styles:**

```css
.card-match {
    background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
}

.match-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-4) var(--space-6);
    border-bottom: 1px solid var(--border-secondary);
}

.match-round {
    font-size: var(--text-xs);
    font-weight: var(--font-bold);
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

.match-status {
    padding: var(--space-1) var(--space-3);
    border-radius: var(--radius-full);
    font-size: var(--text-xs);
    font-weight: var(--font-bold);
}

.match-status-live {
    background: rgba(6, 182, 212, 0.2);
    color: var(--neon-cyan);
    border: 1px solid var(--neon-cyan);
    animation: pulse 2s infinite;
}

.match-teams {
    padding: var(--space-6);
}

.team {
    display: flex;
    align-items: center;
    gap: var(--space-4);
    padding: var(--space-4);
    border-radius: var(--radius-base);
    transition: var(--transition-base);
}

.team:hover {
    background: var(--bg-hover);
}

.team-winner {
    background: rgba(59, 130, 246, 0.1);
    border: 1px solid rgba(59, 130, 246, 0.3);
}

.team-logo {
    width: 40px;
    height: 40px;
    border-radius: var(--radius-base);
    object-fit: cover;
}

.team-name {
    flex: 1;
    font-weight: var(--font-medium);
    color: var(--text-primary);
}

.team-score {
    font-size: var(--text-2xl);
    font-weight: var(--font-bold);
    color: var(--brand-primary);
}

.match-divider {
    display: flex;
    justify-content: center;
    margin: var(--space-2) 0;
}

.match-vs {
    font-size: var(--text-sm);
    font-weight: var(--font-bold);
    color: var(--text-tertiary);
}

.match-footer {
    display: flex;
    gap: var(--space-3);
    padding: var(--space-4) var(--space-6);
    border-top: 1px solid var(--border-secondary);
}
```

---

### 4.3 Form Elements

**Input Fields:**

```html
<!-- Text Input -->
<div class="form-group">
    <label class="form-label" for="tournament-name">
        Tournament Name
        <span class="form-required">*</span>
    </label>
    <input 
        type="text" 
        id="tournament-name" 
        class="form-input" 
        placeholder="Enter tournament name"
        required
    >
    <span class="form-hint">This will be displayed publicly</span>
</div>

<!-- Input with Icon -->
<div class="form-group">
    <label class="form-label" for="search">Search</label>
    <div class="input-group">
        <span class="input-icon input-icon-left">
            <svg class="icon-sm"><!-- Search icon --></svg>
        </span>
        <input 
            type="search" 
            id="search" 
            class="form-input input-with-icon-left" 
            placeholder="Search tournaments..."
        >
    </div>
</div>

<!-- Input with Error -->
<div class="form-group form-group-error">
    <label class="form-label" for="email">Email</label>
    <input 
        type="email" 
        id="email" 
        class="form-input form-input-error" 
        value="invalidemail"
        aria-invalid="true"
        aria-describedby="email-error"
    >
    <span class="form-error" id="email-error">
        <svg class="icon-sm"><!-- Alert icon --></svg>
        Please enter a valid email address
    </span>
</div>

<!-- Input with Success -->
<div class="form-group form-group-success">
    <label class="form-label" for="username">Username</label>
    <input 
        type="text" 
        id="username" 
        class="form-input form-input-success" 
        value="player123"
    >
    <span class="form-success">
        <svg class="icon-sm"><!-- Check icon --></svg>
        Username is available
    </span>
</div>
```

**Form Styles:**

```css
.form-group {
    margin-bottom: var(--space-6);
}

.form-label {
    display: block;
    margin-bottom: var(--space-2);
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text-primary);
}

.form-required {
    color: var(--error);
    margin-left: var(--space-1);
}

.form-input {
    width: 100%;
    padding: var(--space-3) var(--space-4);
    font-size: var(--text-base);
    color: var(--text-primary);
    background: var(--bg-tertiary);
    border: 2px solid var(--border-primary);
    border-radius: var(--radius-base);
    transition: var(--transition-base);
}

.form-input:hover {
    border-color: var(--border-accent);
}

.form-input:focus {
    outline: none;
    border-color: var(--brand-primary);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-input::placeholder {
    color: var(--text-tertiary);
}

.form-input:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    background: var(--bg-secondary);
}

/* Input with icon */
.input-group {
    position: relative;
}

.input-icon {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-tertiary);
}

.input-icon-left {
    left: var(--space-4);
}

.input-icon-right {
    right: var(--space-4);
}

.input-with-icon-left {
    padding-left: calc(var(--space-4) + var(--icon-sm) + var(--space-2));
}

.input-with-icon-right {
    padding-right: calc(var(--space-4) + var(--icon-sm) + var(--space-2));
}

/* Error state */
.form-input-error {
    border-color: var(--error);
}

.form-input-error:focus {
    box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}

.form-error {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin-top: var(--space-2);
    font-size: var(--text-sm);
    color: var(--error);
}

/* Success state */
.form-input-success {
    border-color: var(--success);
}

.form-input-success:focus {
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
}

.form-success {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin-top: var(--space-2);
    font-size: var(--text-sm);
    color: var(--success);
}

/* Hint text */
.form-hint {
    display: block;
    margin-top: var(--space-2);
    font-size: var(--text-sm);
    color: var(--text-tertiary);
}
```

**Select Dropdown:**

```html
<div class="form-group">
    <label class="form-label" for="game">Game</label>
    <div class="select-wrapper">
        <select id="game" class="form-select">
            <option value="">Select a game</option>
            <option value="valorant">VALORANT</option>
            <option value="efootball">eFootball</option>
            <option value="pubgm">PUBG Mobile</option>
            <option value="freefire">Free Fire</option>
        </select>
        <span class="select-icon">
            <svg class="icon-sm"><!-- Chevron down --></svg>
        </span>
    </div>
</div>
```

```css
.select-wrapper {
    position: relative;
}

.form-select {
    width: 100%;
    padding: var(--space-3) calc(var(--space-10)) var(--space-3) var(--space-4);
    font-size: var(--text-base);
    color: var(--text-primary);
    background: var(--bg-tertiary);
    border: 2px solid var(--border-primary);
    border-radius: var(--radius-base);
    appearance: none;
    cursor: pointer;
    transition: var(--transition-base);
}

.form-select:hover {
    border-color: var(--border-accent);
}

.form-select:focus {
    outline: none;
    border-color: var(--brand-primary);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.select-icon {
    position: absolute;
    right: var(--space-4);
    top: 50%;
    transform: translateY(-50%);
    pointer-events: none;
    color: var(--text-tertiary);
}
```

---

**End of Part 4.1: UI/UX Design Foundations**

---

**Navigation:**  
← [Previous: PART_3.2_DATABASE_CONSTRAINTS_MIGRATION.md](PART_3.2_DATABASE_CONSTRAINTS_MIGRATION.md) | [Next: PART_4.2 (Tournament & Registration Screens - Coming Soon)](PART_4.2_TOURNAMENT_REGISTRATION_SCREENS.md) →
